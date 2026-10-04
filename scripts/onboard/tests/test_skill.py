import re
import subprocess
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
        self.assertEqual(set(), set(keys) - onboard.PROJECT_KEYS)
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

    def test_calibrate_reused_by_reference(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("skills/configure/calibrate/SKILL.md", text)
        self.assertTrue(CALIBRATE.is_file())


if __name__ == "__main__":
    unittest.main()
