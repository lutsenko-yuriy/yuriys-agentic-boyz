import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.onboard import bash_policy, gate, onboard

ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = ROOT / "skills" / "configure" / "onboard"
SKILL = SKILL_DIR / "SKILL.md"
RESOURCES = SKILL_DIR / "resources"
STUB = ROOT / ".claude" / "commands" / "onboard.md"
CALIBRATE = ROOT / "skills" / "configure" / "calibrate" / "SKILL.md"

WRITE_RE = re.compile(r"\b(?:Edit|Write|Create)\s+`([^`\s]+)`")
BASH_FENCE_RE = re.compile(r"^```bash\n(.*?)^```", re.MULTILINE | re.DOTALL)
INLINE_CMD_RE = re.compile(r"`((?:python3[\w.]*|/\S*python3[\w.]*|git|gh|ls|cat|grep|rg|find|head|tail|wc) [^`]*)`")
MCP_RE = re.compile(r"\bmcp__\w+__\w+")


def skill_files():
    return [SKILL] + sorted(RESOURCES.glob("*.md"))


def text_of(paths):
    return "\n".join(p.read_text(encoding="utf-8") for p in paths)


def block(name, text):
    m = re.search(r"<!-- onboard:%s\b(.*?)-->" % name, text, re.DOTALL)
    return m.group(1) if m else None


def declared_writes(text):
    m = re.search(r"<!-- onboard:writes -->(.*?)<!-- /onboard:writes -->", text, re.DOTALL)
    return re.findall(r"^- `([^`]+)`", m.group(1), re.MULTILINE) if m else []


def bash_lines(text):
    lines = []
    for body in BASH_FENCE_RE.findall(text):
        lines += [ln.strip() for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    return lines + INLINE_CMD_RE.findall(text)


class SkillFilesTest(unittest.TestCase):
    def test_files_exist(self):
        for p in (SKILL, RESOURCES / "orientation.md", RESOURCES / "artifact-guide.md", STUB):
            self.assertTrue(p.is_file(), p)

    def test_frontmatter(self):
        head = SKILL.read_text(encoding="utf-8").split("---")[1]
        fm = dict(re.findall(r"^(\w+):\s*(.*)$", head, re.MULTILINE))
        self.assertEqual("onboard", fm["name"])
        for key in ("effort", "reasoning", "description"):
            self.assertTrue(fm.get(key), key)

    def test_stub_runs_inline(self):
        stub = STUB.read_text(encoding="utf-8")
        self.assertIn("skills/configure/onboard/SKILL.md", stub)
        for banned in ("skill_router", "subagent", "Agent"):
            self.assertNotIn(banned, stub)

    def test_no_known_placeholder_tokens(self):
        # apply would substitute them and check would flag them; the skill must not contain any.
        for p in skill_files() + [STUB]:
            self.assertEqual([], onboard.PLACEHOLDER_RE.findall(p.read_text(encoding="utf-8")), p)

    def test_no_spawning_or_other_skills(self):
        text = text_of(skill_files())
        self.assertNotRegex(text, r"(?i)\bspawn")
        self.assertNotRegex(text, r"(?i)Agent tool|\bSkill tool")


class WritePathsTest(unittest.TestCase):
    def test_declared_writes_are_bootstrap_paths(self):
        declared = declared_writes(SKILL.read_text(encoding="utf-8"))
        self.assertTrue(declared)
        for path in declared:
            self.assertIn(path, gate.BOOTSTRAP_PATHS)

    def test_every_write_instruction_is_declared_and_allowed(self):
        text = text_of(skill_files())
        declared = set(declared_writes(SKILL.read_text(encoding="utf-8")))
        found = set(WRITE_RE.findall(text))
        self.assertTrue(found)
        self.assertEqual(set(), found - declared, "write instruction for an undeclared path")
        self.assertEqual(set(), declared - found, "declared path with no write instruction")
        for path in found:
            self.assertIn(path, gate.BOOTSTRAP_PATHS)

    def test_artifacts_all_written(self):
        found = set(WRITE_RE.findall(text_of(skill_files())))
        for rel in onboard.ARTIFACTS + ["skill_router.toml", "docs/MODEL_TIERS.md"]:
            self.assertIn(rel, found)

    def test_never_writes_command_stubs(self):
        self.assertNotRegex(text_of(skill_files()), r"(?i)(Edit|Write|Create|update)\s+`?\.claude/commands")


class BashAndToolsTest(unittest.TestCase):
    def test_every_command_is_allowlisted(self):
        cmds = bash_lines(text_of(skill_files()))
        self.assertTrue(cmds)
        for cmd in cmds:
            allowed, reason = bash_policy.is_allowed(cmd)
            self.assertTrue(allowed, "%s: %s" % (cmd, reason))

    def test_all_four_subcommands_used(self):
        cmds = " ".join(bash_lines(text_of(skill_files())))
        for sub in sorted(bash_policy.ONBOARD_SUBCOMMANDS):
            self.assertIn("scripts/onboard/onboard.py %s" % sub, cmds)

    def test_never_uses_force(self):
        self.assertNotIn("--force", " ".join(bash_lines(text_of(skill_files()))))

    def test_mcp_tools_are_read_verbs(self):
        for name in MCP_RE.findall(text_of(skill_files())):
            self.assertTrue(name.split("__", 2)[2].startswith(gate.MCP_READ_PREFIXES), name)

    def test_declared_tools_pass_the_gate(self):
        tools = block("tools", SKILL.read_text(encoding="utf-8"))
        self.assertIsNotNone(tools)
        allowed = gate.PASS_TOOLS | set(gate.WRITE_TOOLS) | {"Bash"}
        names = [t.strip() for t in tools.replace("\n", " ").split(",") if t.strip()]
        self.assertTrue(names)
        for name in names:
            self.assertIn(name, allowed)
        self.assertIn("AskUserQuestion", names)


class ConfigAgreementTest(unittest.TestCase):
    def test_project_keys_are_known_and_required_ones_covered(self):
        keys = (block("project-keys", SKILL.read_text(encoding="utf-8")) or "").split()
        self.assertTrue(keys)
        self.assertEqual(onboard.PROJECT_KEYS, set(keys))
        for field in onboard.REQUIRED_PROJECT_FIELDS:
            self.assertIn(field, keys)

    def test_pm_choices_match_providers(self):
        text = text_of(skill_files())
        for pm in onboard.PM_TOOLS:
            self.assertIn('"%s"' % pm, text)
        self.assertNotIn("github_issues", text)

    def test_manual_placeholders_are_named(self):
        # Placeholders apply never fills, still present in tracked files, must have a manual step in the skill.
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, text=True).stdout
        manual = set(onboard.KNOWN_PLACEHOLDERS) - set(onboard.PLACEHOLDER_FIELDS) - {"PM_TOOL"}
        present = set()
        for rel in (f for f in out.split("\0") if f and onboard._scanned(f)):
            if rel in ("README.md", "setup.sh") or rel.startswith("skills/configure/onboard/"):
                continue  # README is rewritten and setup.sh deleted in the cutover WUs
            try:
                found = onboard.PLACEHOLDER_RE.findall((ROOT / rel).read_text(encoding="utf-8"))
            except (UnicodeDecodeError, OSError):
                continue
            present |= {f[2:-2] for f in found}
        text = text_of(skill_files())
        for name in sorted(manual & present):
            self.assertIn("`%s`" % name, text)  # the bare backticked name, not e.g. CODE_STYLE.md

    def test_every_key_needs_a_concrete_value(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertRegex(text, r"never leave a key empty")
        self.assertIn("`none`", text)
        self.assertNotRegex(text, r"(?i)leave a key empty if")

    def test_calibrate_step_forbids_shell_and_fetching(self):
        step = SKILL.read_text(encoding="utf-8").split("### 7.")[1].split("### 8.")[0]
        self.assertRegex(step, r"(?i)do not run any shell")
        self.assertRegex(step, r"(?i)ask the user for the model ids")

    def test_calibrate_reused_by_reference(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("skills/configure/calibrate/SKILL.md", text)
        self.assertTrue(CALIBRATE.is_file())


class NoStrayWriteVerbsTest(unittest.TestCase):
    VERB_RE = re.compile(r"\b(edit|write|create|modify|append|update|change)\s+(?!`)", re.IGNORECASE)

    def test_write_verbs_are_followed_by_a_listed_path(self):
        offenders = []
        for p in skill_files():
            for ln in p.read_text(encoding="utf-8").splitlines():
                if self.VERB_RE.search(ln) and not ln.lstrip().startswith("description:"):
                    offenders.append("%s: %s" % (p.name, ln.strip()[:100]))
        self.assertEqual([], offenders)


def make_clone(parent, origin=None, sentinel=False):
    """A scratch git repo holding this working tree's tracked files (README/setup.sh are out of scope here)."""
    dest = Path(parent) / "clone"
    dest.mkdir()
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, text=True, check=True).stdout
    for rel in (f for f in out.split("\0") if f):
        src = ROOT / rel
        if src.is_file() and not src.is_symlink():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / rel)
    subprocess.run(["git", "-C", str(dest), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(dest), "add", "-A"], check=True)  # apply and check only see tracked files
    if origin:
        subprocess.run(["git", "-C", str(dest), "remote", "add", "origin", origin], check=True)
    if sentinel:
        (dest / ".yab-template").write_text("repo=%s\n" % onboard.YAB_REPO)
    return dest.resolve()


def has_tomllib():
    try:
        import tomllib  # noqa: F401
        return True
    except ImportError:
        return False


def write_config(root, empty=()):
    project = {k: "none" for k in onboard.PROJECT_KEYS if k != "keep_licence"}
    project.update(name="Demo", description="A demo", issue_prefix="DEM", architecture_summary="Layered")
    for key in empty:
        project[key] = ""
    lines = ['[providers]', 'pm = "github"', 'vcs = "github"', "", "[project]"]
    lines += ['%s = %s' % (k, json.dumps(v)) for k, v in sorted(project.items())]
    (root / "skill_router.toml").write_text("\n".join(lines) + "\n")


def stranded(root):
    """Placeholders left after apply in files the skill may not write."""
    writes = set(declared_writes(SKILL.read_text(encoding="utf-8")))
    left = {}
    for rel in onboard._tracked_files(root):
        if rel in ("README.md", "setup.sh") or not onboard._scanned(rel) or not (root / rel).is_file():
            continue
        found = onboard.PLACEHOLDER_RE.findall((root / rel).read_text(encoding="utf-8"))
        if found and rel not in writes:
            left[rel] = found
    return left


@unittest.skipUnless(has_tomllib(), "needs Python 3.11+")
class ApplyEndToEndTest(unittest.TestCase):
    def test_concrete_values_leave_no_placeholder_outside_the_writes_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_clone(tmp)
            write_config(root)
            onboard.apply(root)
            self.assertEqual({}, stranded(root))

    def test_an_empty_value_would_strand_onboarding(self):
        # Why the skill demands `none`: this placeholder lives in a file the gate will not let the agent edit.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_clone(tmp)
            write_config(root, empty=["experiment_tool"])
            onboard.apply(root)
            self.assertIn("docs/experiments/README.md", stranded(root))


@unittest.skipUnless(has_tomllib(), "needs Python 3.11+")
class TemplateFlowTest(unittest.TestCase):
    """State table: sentinel x origin x answer.

    no sentinel                 -> ordinary flow (setup-incomplete or configured)
    sentinel, origin YAB, (a)   -> template_mode; agent runs plain `mark` (check is ok in template mode)
    sentinel, origin YAB, (b)   -> template_mode; apply refuses; human repoints origin, then as the next row
    sentinel, origin not YAB    -> template_mode false + sentinel error; ordinary flow; apply deletes the sentinel
    (fork maintenance: the human runs `mark --force`, the one case where check stays not ok)
    """

    YAB_URL = "https://github.com/%s.git" % onboard.YAB_REPO

    def test_yab_origin_is_template_mode_and_plain_mark_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_clone(tmp, self.YAB_URL, sentinel=True)
            result = onboard.check(root)
            self.assertTrue(result["template_mode"])
            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(0, onboard.mark(root, force=False))

    def test_yab_origin_refuses_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_clone(tmp, self.YAB_URL, sentinel=True)
            write_config(root)
            with self.assertRaises(onboard.Refused):
                onboard.apply(root)

    def test_after_repointing_origin_the_flow_continues_and_apply_removes_the_sentinel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_clone(tmp, self.YAB_URL, sentinel=True)
            subprocess.run(["git", "-C", str(root), "remote", "set-url", "origin", "https://github.com/me/proj.git"], check=True)
            result = onboard.check(root)
            self.assertFalse(result["template_mode"])
            self.assertTrue(any(".yab-template present" in e for e in result["errors"]))
            write_config(root)
            self.assertTrue(onboard.apply(root)["sentinel_deleted"])
            self.assertFalse((root / ".yab-template").exists())
            self.assertFalse(any(".yab-template" in e for e in onboard.check(root)["errors"]))

    def test_origin_not_yab_never_asks_the_template_question(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("`template_mode` is true", text)
        self.assertIn(".yab-template present", text)

    def test_human_only_commands_are_marked_and_limited(self):
        text = text_of(skill_files())
        human = [c for c in re.findall(r"`(! [^`]+)`", text)]
        self.assertTrue(any("git remote set-url origin" in c for c in human))
        self.assertTrue(any("onboard.py mark --force" in c for c in human))
        for c in human:
            self.assertTrue("set-url origin" in c or "mark --force" in c, c)
        # Outside those `! ` commands the agent must never be told to run set-url or --force.
        stripped = re.sub(r"`! [^`]+`", "", text)
        self.assertNotIn("set-url", stripped)
        self.assertNotIn("--force", stripped)


class RegistrationTest(unittest.TestCase):
    def test_agents_md_lists_onboard_and_scopes_calibrate(self):
        rows = [ln for ln in (ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines() if ln.startswith("| skills/")]
        onboard_row = [ln for ln in rows if "skills/configure/onboard/SKILL.md" in ln]
        self.assertEqual(1, len(onboard_row))
        calibrate_row = next(ln for ln in rows if "skills/configure/calibrate/SKILL.md" in ln)
        self.assertIn("re-map", calibrate_row.lower())
        self.assertIn("/onboard", calibrate_row)


if __name__ == "__main__":
    unittest.main()
