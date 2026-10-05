import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from scripts.onboard import onboard
from scripts.onboard.tests.test_onboard import YAB_ORIGIN, YAB_SENTINEL, git, make_repo, needs_toml

REPO = Path(__file__).resolve().parents[3]

# placeholder -> (toml [project] field, value used in tests)
FIELD_CASES = {
    "PROJECT_NAME": ("name", "Habit Loop"),
    "PROJECT_DESCRIPTION": ("description", "Build habits"),
    "ARCHITECTURE_SUMMARY": ("architecture_summary", "Vertical slices"),
    "ISSUE_PREFIX": ("issue_prefix", "HL"),
    "GIT_HOST": ("git_host", "GitHub"),
    "PM_PROJECT_URL": ("pm_project_url", "https://linear.app/x"),
    "TEAM_ID": ("team_id", "team-1"),
    "PROJECT_ID": ("project_id", "proj-1"),
    "EXPERIMENT_TOOL": ("experiment_tool", "Firebase"),
    "AVAILABLE_MODELS": ("available_models", "opus, sonnet"),
    "AI_COMMIT_TRAILER": ("ai_commit_trailer", "Co-Authored-By: X"),
    "AI_TOOL_CREDIT": ("ai_tool_credit", "Claude Code"),
    "TEST_COMMAND": ("test_command", "flutter test"),
    "INTEGRATION_TEST_DIR": ("integration_test_dir", "integration_test/"),
    "TEST_HARNESS_FILE": ("test_harness_file", "integration_test/harness.dart"),
    "TEST_HARNESS_CLASS": ("test_harness_class", "AppHarness"),
    "VERSION_FILE": ("version_file", "pubspec.yaml"),
    "VERSION_FIELD": ("version_field", "version"),
    "IN_QA_PATHS": ("in_qa_paths", "lib/"),
}
PM_CASES = {"linear": "Linear", "github": "GitHub Issues"}
# Left to later work units (tech-stack artifacts): apply must never touch them.
UNMAPPED = ["CODE_STYLE", "FRAMEWORK", "PERSISTENCE", "STACK", "STATE_MANAGEMENT"]


def toml_text(pm="linear", extra="", **project):
    lines = ['[providers]', 'pm = "%s"' % pm, '', '[project]']
    lines += ['%s = %s' % (k, json.dumps(v)) for k, v in project.items()]
    return "\n".join(lines) + "\n" + extra


def ph(name):
    return "{{%s}}" % name


def full_toml(pm="linear", **extra):
    project = {field: value for field, value in FIELD_CASES.values()}
    project.update(extra)
    return toml_text(pm, **project)


def run_apply(root, *extra, cwd=None):
    out, err = io.StringIO(), io.StringIO()
    old = os.getcwd()
    try:
        if cwd:
            os.chdir(cwd)
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = onboard.main(list(extra) + ["apply"])
            except SystemExit as e:  # load_toml exits 2 itself when tomllib is missing
                code = e.code
    finally:
        os.chdir(old)
    return code, out.getvalue(), err.getvalue()


def snapshot(root):
    return {
        str(p.relative_to(root)): p.read_bytes() if p.is_file() and not p.is_symlink() else os.readlink(p) if p.is_symlink() else None
        for p in sorted(Path(root).rglob("*")) if ".git" not in p.relative_to(root).parts
    }


@needs_toml
class SchemaTests(unittest.TestCase):
    def test_template_toml_has_every_mapped_field_empty_and_pm_present_but_empty(self):
        import tomllib

        cfg = tomllib.loads((REPO / "skill_router.toml").read_text(encoding="utf-8"))
        project = cfg["project"]
        for field, _ in FIELD_CASES.values():
            self.assertEqual(project[field], "", field)
        self.assertIs(project["keep_licence"], True)
        self.assertEqual(cfg["providers"]["pm"], "")

    def test_every_known_placeholder_is_mapped_or_deliberately_left(self):
        mapped = set(FIELD_CASES) | {"PM_TOOL"} | set(UNMAPPED)
        self.assertEqual(mapped, set(onboard.KNOWN_PLACEHOLDERS))


@needs_toml
class SubstitutionTests(unittest.TestCase):
    def repo(self, tmp, toml, files=None, origin=None):
        files = dict(files or {})
        files["skill_router.toml"] = toml
        return make_repo(tmp, files, origin)

    def test_each_field_maps_to_its_placeholder(self):
        for name, (field, value) in FIELD_CASES.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                root = self.repo(tmp, toml_text(**{field: value}), {"a.md": "x %s y\n" % ph(name)})
                code, _, err = run_apply(root, "--root", str(root))
                self.assertEqual(code, 0, err)
                self.assertEqual((root / "a.md").read_text(), "x %s y\n" % value)

    def test_pm_tool_derived_from_providers_pm(self):
        for pm, label in PM_CASES.items():
            with self.subTest(pm), tempfile.TemporaryDirectory() as tmp:
                root = self.repo(tmp, toml_text(pm), {"a.md": ph("PM_TOOL")})
                self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
                self.assertEqual((root / "a.md").read_text(), label)

    def test_unknown_pm_is_an_error_and_writes_nothing(self):
        for pm in ["trello", "jira", "github_issues", "files"]:
            with self.subTest(pm), tempfile.TemporaryDirectory() as tmp:
                root = self.repo(tmp, toml_text(pm, name="N"), {"a.md": ph("PROJECT_NAME")})
                before = snapshot(root)
                code, _, err = run_apply(root, "--root", str(root))
                self.assertEqual(code, 3)
                self.assertIn(pm, err)
                self.assertEqual(snapshot(root), before)

    def test_pm_tools_are_skill_router_providers(self):
        from scripts.skill_router.providers import PROVIDER_REGISTRY
        self.assertLessEqual(set(onboard.PM_TOOLS), set(PROVIDER_REGISTRY))

    def test_invalid_issue_prefix_is_rejected_before_any_write(self):
        for prefix in ["N/A", "na", "my app", "X", "1AB", "TOOLONGPREFIX"]:
            with self.subTest(prefix), tempfile.TemporaryDirectory() as tmp:
                root = self.repo(tmp, toml_text(issue_prefix=prefix), {"a.md": ph("ISSUE_PREFIX")})
                before = snapshot(root)
                code, _, err = run_apply(root, "--root", str(root))
                self.assertEqual(code, 3)
                self.assertIn("issue_prefix", err)
                self.assertEqual(snapshot(root), before)

    def test_multiline_value_is_rejected_before_any_write(self):
        for value in ["a\nb", "a\r\nb", ["a\nb"]]:
            with self.subTest(value), tempfile.TemporaryDirectory() as tmp:
                root = self.repo(tmp, toml_text(description=value) if isinstance(value, str)
                                 else toml_text(available_models=value), {"a.md": ph("PROJECT_DESCRIPTION")})
                before = snapshot(root)
                code, _, err = run_apply(root, "--root", str(root))
                self.assertEqual(code, 3)
                self.assertIn("single line", err)
                self.assertEqual(snapshot(root), before)

    def test_unknown_project_keys_are_warned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp, toml_text(name="N", keep_license=False), {"a.md": ph("PROJECT_NAME")})
            code, out, _ = run_apply(root, "--root", str(root))
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["warnings"], ["skill_router.toml: unknown project.keep_license ignored"])

    def test_empty_values_leave_placeholders_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp, toml_text("", name="  ", issue_prefix="HL"),
                             {"a.md": "%s %s %s\n" % (ph("PROJECT_NAME"), ph("ISSUE_PREFIX"), ph("PM_TOOL"))})
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertEqual((root / "a.md").read_text(), "%s HL %s\n" % (ph("PROJECT_NAME"), ph("PM_TOOL")))
            self.assertEqual(onboard.check(root)["placeholders"]["a.md"], [ph("PM_TOOL"), ph("PROJECT_NAME")])

    def test_values_are_stripped_and_list_values_joined(self):
        with tempfile.TemporaryDirectory() as tmp:
            toml = toml_text(name="  Padded  ", available_models=["opus", " sonnet ", ""], in_qa_paths=["lib/", "ios/"])
            root = self.repo(tmp, toml, {"a.md": "%s|%s|%s" % tuple(map(ph, ["PROJECT_NAME", "AVAILABLE_MODELS", "IN_QA_PATHS"]))})
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertEqual((root / "a.md").read_text(), "Padded|opus, sonnet|lib/, ios/")

    def test_regex_metacharacters_in_values_are_literal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp, toml_text(name=r"A\1 \g<0> $&"), {"a.md": ph("PROJECT_NAME")})
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertEqual((root / "a.md").read_text(), r"A\1 \g<0> $&")

    def test_value_containing_a_placeholder_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp, toml_text(name="x " + ph("TEAM_ID")), {"a.md": ph("PROJECT_NAME")})
            code, _, err = run_apply(root, "--root", str(root))
            self.assertEqual(code, 3)
            self.assertIn("project.name", err)
            self.assertEqual((root / "a.md").read_text(), ph("PROJECT_NAME"))

    def test_non_string_value_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp, toml_text(name=5), {"a.md": ph("PROJECT_NAME")})
            code, _, err = run_apply(root, "--root", str(root))
            self.assertEqual(code, 3)
            self.assertIn("project.name", err)

    def test_unmapped_placeholders_stay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp, full_toml(), {"a.md": " ".join(ph(n) for n in UNMAPPED)})
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertEqual((root / "a.md").read_text(), " ".join(ph(n) for n in UNMAPPED))

    def test_missing_project_table_is_all_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp, '[providers]\npm = "github"\n', {"a.md": ph("PROJECT_NAME") + ph("PM_TOOL")})
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertEqual((root / "a.md").read_text(), ph("PROJECT_NAME") + "GitHub Issues")

    def test_escaped_braces_and_unknown_names_untouched(self):
        text = 'f"{{{PROJECT_NAME}}}" ${{PROJECT_NAME}} {{OTHER}}\n'
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp, toml_text(name="N"), {"a.md": text})
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertEqual((root / "a.md").read_text(), text)

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp, full_toml(), {"a.md": " ".join(ph(n) for n in FIELD_CASES), "b/c.md": ph("PM_TOOL")})
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            after_first = snapshot(root)
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "applied")
            code, out, _ = run_apply(root, "--root", str(root))
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["changed"], [])
            self.assertEqual(git(root, "status", "--porcelain"), "")
            self.assertEqual(snapshot(root), after_first)


@needs_toml
class FileSelectionTests(unittest.TestCase):
    def apply_in(self, files, toml=None, setup=None, origin=None):
        with tempfile.TemporaryDirectory() as tmp:
            files = dict(files)
            files["skill_router.toml"] = toml or toml_text(name="N")
            root = make_repo(tmp, files, origin)
            if setup:
                setup(root)
            code, out, err = run_apply(root, "--root", str(root))
            return code, err, {rel: (root / rel).read_bytes() if (root / rel).is_file() else None for rel in files}, root

    def test_untracked_files_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text(name="N")})
            (root / "u.md").write_text("plain\n")
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertEqual((root / "u.md").read_text(), "plain\n")
            (root / "v.md").write_text(ph("PROJECT_NAME"))  # untracked with a placeholder: refused, never filled
            self.assertNotEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertEqual((root / "v.md").read_text(), ph("PROJECT_NAME"))

    def test_skipped_paths_untouched_but_knowledge_templates_scanned(self):
        t = ph("PROJECT_NAME")
        files = {
            "scripts/onboard/x.md": t, "docs/CHANGELOG.md": t, "docs/knowledge/notes/HAB-1.md": t,
            "docs/knowledge/README.md": t, "docs/knowledge/notes/TEMPLATE.md": t, "docs/other.md": t,
        }
        code, err, res, _ = self.apply_in(files)
        self.assertEqual(code, 0, err)
        for rel in ("scripts/onboard/x.md", "docs/CHANGELOG.md", "docs/knowledge/notes/HAB-1.md"):
            self.assertEqual(res[rel], t.encode(), rel)
        for rel in ("docs/knowledge/README.md", "docs/knowledge/notes/TEMPLATE.md", "docs/other.md"):
            self.assertEqual(res[rel], b"N", rel)

    def test_symlinks_not_followed_and_target_untouched(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "t.md"
            target.write_text(ph("PROJECT_NAME"))
            root = make_repo(tmp, {"skill_router.toml": toml_text(name="N")})
            os.symlink(target, root / "link.md")
            os.symlink("real.md", root / "rel.md")
            (root / "real.md").write_text(ph("PROJECT_NAME"))
            git(root, "add", "-A")
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertEqual(target.read_text(), ph("PROJECT_NAME"))
            self.assertTrue((root / "link.md").is_symlink() and (root / "rel.md").is_symlink())
            self.assertEqual(os.readlink(root / "link.md"), str(target))
            self.assertEqual((root / "real.md").read_text(), "N")

    def test_non_utf8_oversized_and_deleted_files_are_skipped_not_fatal(self):
        def setup(root):
            (root / "gone.md").unlink()

        files = {"bin.dat": None, "big.md": ph("PROJECT_NAME") + "x" * 1_000_001, "gone.md": ph("PROJECT_NAME"),
                 "ok.md": ph("PROJECT_NAME")}
        with tempfile.TemporaryDirectory() as tmp:
            files["skill_router.toml"] = toml_text(name="N")
            root = make_repo(tmp, {k: v for k, v in files.items() if v is not None})
            raw = b"\xff\xfe" + ph("PROJECT_NAME").encode()
            (root / "bin.dat").write_bytes(raw)
            git(root, "add", "-A")
            setup(root)
            code, _, err = run_apply(root, "--root", str(root))
            self.assertEqual(code, 0, err)
            self.assertEqual((root / "bin.dat").read_bytes(), raw)
            self.assertTrue((root / "big.md").read_text().startswith(ph("PROJECT_NAME")))
            self.assertEqual((root / "ok.md").read_text(), "N")

    def test_crlf_and_mode_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text(name="N"), "a.md": "a\r\n%s\r\n" % ph("PROJECT_NAME"),
                                   "run.sh": "echo %s\n" % ph("PROJECT_NAME")})
            os.chmod(root / "run.sh", 0o755)
            os.chmod(root / "a.md", 0o444)
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertEqual((root / "a.md").read_bytes(), b"a\r\nN\r\n")
            self.assertEqual(stat.S_IMODE((root / "run.sh").stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((root / "a.md").stat().st_mode), 0o444)

    def test_nothing_tracked_refuses_and_keeps_sentinel(self):
        t = ph("PROJECT_NAME")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text(name="N"), "a.md": t, ".yab-template": "repo=other/x\n"})
            subprocess.run(["git", "-C", str(root), "rm", "-r", "-q", "--cached", "."], check=True)
            before = snapshot(root)
            code, _, err = run_apply(root, "--root", str(root))
            self.assertNotEqual(code, 0)
            self.assertIn("tracked by git", err)
            self.assertEqual(before, snapshot(root))

    def test_retrofit_with_only_named_files_added_cannot_be_marked(self):
        # Existing repo (one commit), YAB files copied in; only the 4 named files are `git add`-ed.
        t = ph("PROJECT_NAME")
        named = ["skill_router.toml", "docs/TECH_STACK.md", "docs/CODE_STYLE.md", "docs/CONSTRAINTS.md"]
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"main.py": "x\n"})
            subprocess.run(["git", "-C", str(root), "rm", "-r", "-q", "--cached", "."], check=True)
            (root / "skill_router.toml").write_text(toml_text(name="N"))
            subprocess.run(["git", "-C", str(root), "add", "main.py"] + named, check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "retrofit"], check=True)
            (root / "AGENTS.md").write_text(t)  # untracked, holds a placeholder
            before = snapshot(root)
            code, _, err = run_apply(root, "--root", str(root))
            self.assertNotEqual(code, 0)
            self.assertIn("AGENTS.md", err)
            self.assertEqual(before, snapshot(root))
            res = onboard.check(root)
            self.assertFalse(res["ok"])
            self.assertIn("AGENTS.md", " ".join(res["errors"]))
            self.assertNotEqual(0, onboard.mark(root, False))

    def test_ignored_untracked_placeholder_files_are_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {".gitignore": "scratch.md\n"})
            (root / "scratch.md").write_text(ph("PROJECT_NAME"))
            self.assertNotIn("scratch.md", " ".join(onboard.check(root)["errors"]))

    def test_unchanged_files_are_not_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text("", name="N"), "a.md": "plain\n"})
            with mock.patch("os.replace", side_effect=AssertionError("no write expected")):
                self.assertEqual(run_apply(root, "--root", str(root))[0], 0)

    def test_partial_failure_leaves_whole_files_no_temp_and_keeps_sentinel(self):
        t = ph("PROJECT_NAME")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text(name="N"), "a.md": t, "b.md": t, "c.md": t,
                                   ".yab-template": "repo=other/x\n"})
            real, calls = os.replace, []

            def flaky(src, dst):
                calls.append(dst)
                if len(calls) == 2:
                    raise OSError("disk full")
                return real(src, dst)

            with mock.patch("os.replace", side_effect=flaky):
                code, _, err = run_apply(root, "--root", str(root))
            self.assertEqual(code, 3)
            self.assertIn("disk full", err)
            texts = sorted((root / n).read_text() for n in ("a.md", "b.md", "c.md"))
            self.assertEqual(texts, ["N", t, t])
            self.assertTrue((root / ".yab-template").exists())
            leftovers = [p for p in root.iterdir() if p.name.startswith(".onboard-")]
            self.assertEqual(leftovers, [])
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)  # rerun completes
            self.assertEqual([(root / n).read_text() for n in ("a.md", "b.md", "c.md")], ["N"] * 3)
            self.assertFalse((root / ".yab-template").exists())

    def test_runs_from_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text(name="N"), "a.md": ph("PROJECT_NAME"), "d/x.md": "x"})
            code, _, err = run_apply(root, cwd=root / "d")
            self.assertEqual(code, 0, err)
            self.assertEqual((root / "a.md").read_text(), "N")


@needs_toml
class McpTests(unittest.TestCase):
    LINEAR = {"type": "http", "url": "https://mcp.linear.app/mcp"}

    def run_case(self, pm, mcp, origin=None):
        """mcp: None (absent), a dict (JSON), or a raw string. Returns (code, err, parsed-or-None-or-'absent')."""
        with tempfile.TemporaryDirectory() as tmp:
            files = {"skill_router.toml": toml_text(pm)}
            if mcp is not None:
                files[".mcp.json"] = mcp if isinstance(mcp, str) else json.dumps(mcp)
            root = make_repo(tmp, files)
            code, _, err = run_apply(root, "--root", str(root))
            p = root / ".mcp.json"
            return code, err, (json.loads(p.read_text()) if p.exists() else "absent")

    def test_matrix(self):
        other = {"type": "stdio", "command": "x"}
        custom = {"type": "http", "url": "https://custom"}
        cases = [
            # pm, existing .mcp.json, expected result
            ("linear", None, {"mcpServers": {"linear": self.LINEAR}}),
            ("linear", {"mcpServers": {"linear": self.LINEAR}}, {"mcpServers": {"linear": self.LINEAR}}),
            ("linear", {"mcpServers": {"linear": custom}}, {"mcpServers": {"linear": custom}}),
            ("linear", {"mcpServers": {"o": other}}, {"mcpServers": {"o": other, "linear": self.LINEAR}}),
            ("linear", {}, {"mcpServers": {"linear": self.LINEAR}}),
            ("linear", {"mcpServers": {"linear": "bad"}}, {"mcpServers": {"linear": self.LINEAR}}),
            ("linear", {"other": 1}, {"other": 1, "mcpServers": {"linear": self.LINEAR}}),
            ("github", None, "absent"),
            ("github", {"mcpServers": {"linear": self.LINEAR}}, "absent"),
            ("github", {"mcpServers": {"linear": self.LINEAR, "o": other}}, {"mcpServers": {"o": other}}),
            ("github", {"mcpServers": {"o": other}}, {"mcpServers": {"o": other}}),
            ("github", {"mcpServers": {}}, "absent"),
            ("github", {}, "absent"),
            ("github", {"other": 1, "mcpServers": {"linear": self.LINEAR}}, {"other": 1}),
            ("github", {"mcpServers": {"linear": self.LINEAR}}, "absent"),
            ("", None, "absent"),
            ("", {"mcpServers": {"linear": self.LINEAR}}, {"mcpServers": {"linear": self.LINEAR}}),
        ]
        for pm, existing, expected in cases:
            with self.subTest(pm=pm, existing=existing):
                code, err, result = self.run_case(pm, existing)
                self.assertEqual(code, 0, err)
                self.assertEqual(result, expected)

    def test_bad_mcp_json_fails_before_any_write(self):
        for bad in ["{not json", "[]", '{"mcpServers": []}', '"x"']:
            with self.subTest(bad), tempfile.TemporaryDirectory() as tmp:
                root = make_repo(tmp, {"skill_router.toml": toml_text("github", name="N"), ".mcp.json": bad,
                                       "a.md": ph("PROJECT_NAME")})
                code, _, err = run_apply(root, "--root", str(root))
                self.assertEqual(code, 3)
                self.assertIn(".mcp.json", err)
                self.assertEqual((root / "a.md").read_text(), ph("PROJECT_NAME"))

    def test_non_utf8_mcp_json_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text("github")})
            (root / ".mcp.json").write_bytes(b"\xff\xfe")
            self.assertEqual(run_apply(root, "--root", str(root))[0], 3)

    def test_mcp_symlink_refused_and_target_untouched(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "m.json"
            target.write_text(json.dumps({"mcpServers": {"linear": self.LINEAR}}))
            root = make_repo(tmp, {"skill_router.toml": toml_text("github")})
            os.symlink(target, root / ".mcp.json")
            code, _, err = run_apply(root, "--root", str(root))
            self.assertEqual(code, 3)
            self.assertIn(".mcp.json", err)
            self.assertIn("linear", target.read_text())
            self.assertTrue((root / ".mcp.json").is_symlink())

    def test_mcp_directory_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text("github")})
            (root / ".mcp.json").mkdir()
            self.assertEqual(run_apply(root, "--root", str(root))[0], 3)

    def test_existing_formatting_kept_when_already_right(self):
        raw = '{"mcpServers":{"linear":{"type":"http","url":"https://mcp.linear.app/mcp"}}}'
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text("linear"), ".mcp.json": raw})
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertEqual((root / ".mcp.json").read_text(), raw)


@needs_toml
class LicenceAndSentinelTests(unittest.TestCase):
    def run_case(self, project_extra="", files=None, origin=None):
        with tempfile.TemporaryDirectory() as tmp:
            f = {"skill_router.toml": toml_text("github") + project_extra, "LICENSE": "MIT\n"}
            f.update(files or {})
            root = make_repo(tmp, f, origin)
            code, out, err = run_apply(root, "--root", str(root))
            return code, err, {n: (root / n).exists() for n in ("LICENSE", ".yab-template")}, root

    def test_keep_licence_matrix(self):
        # [project] must precede keep_licence, so it is appended right after the table.
        for extra, license_present in [("keep_licence = false\n", False), ("keep_licence = true\n", True), ("", True)]:
            with self.subTest(extra):
                code, err, exists, _ = self.run_case(extra)
                self.assertEqual(code, 0, err)
                self.assertEqual(exists["LICENSE"], license_present)

    def test_keep_licence_false_without_license_file_is_fine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text("github") + "keep_licence = false\n"})
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)

    def test_keep_licence_must_be_boolean(self):
        code, err, exists, _ = self.run_case('keep_licence = "no"\n')
        self.assertEqual(code, 3)
        self.assertIn("keep_licence", err)
        self.assertTrue(exists["LICENSE"])

    def test_keep_licence_false_removes_symlink_not_target(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "L"
            target.write_text("MIT")
            root = make_repo(tmp, {"skill_router.toml": toml_text("github") + "keep_licence = false\n"})
            os.symlink(target, root / "LICENSE")
            self.assertEqual(run_apply(root, "--root", str(root))[0], 0)
            self.assertFalse(os.path.lexists(root / "LICENSE"))
            self.assertEqual(target.read_text(), "MIT")

    def test_sentinel_deleted_when_not_template_mode(self):
        for label, sentinel, origin in [
            ("inherited, no origin", YAB_SENTINEL, None),
            ("inherited, new origin", YAB_SENTINEL, "https://github.com/me/app.git"),
            ("foreign sentinel", "repo=other/x\n", YAB_ORIGIN),
            ("empty sentinel", "", YAB_ORIGIN),
        ]:
            with self.subTest(label):
                code, err, exists, _ = self.run_case(files={".yab-template": sentinel}, origin=origin)
                self.assertEqual(code, 0, err)
                self.assertFalse(exists[".yab-template"])

    def test_no_sentinel_is_fine(self):
        code, err, exists, _ = self.run_case()
        self.assertEqual(code, 0, err)

    def test_template_mode_refuses_and_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": full_toml("github") + "keep_licence = false\n",
                                   ".yab-template": YAB_SENTINEL, "LICENSE": "MIT", "a.md": ph("PROJECT_NAME"),
                                   ".mcp.json": json.dumps({"mcpServers": {"linear": {}}})}, YAB_ORIGIN)
            before = snapshot(root)
            code, out, err = run_apply(root, "--root", str(root))
            self.assertEqual(code, 1)
            self.assertIn("template", err.lower())
            self.assertEqual(out, "")
            self.assertEqual(snapshot(root), before)


@needs_toml
class CliTests(unittest.TestCase):
    def test_summary_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text("github", name="N"), "a.md": ph("PROJECT_NAME") + ph("TEAM_ID")})
            code, out, _ = run_apply(root, "--root", str(root))
            report = json.loads(out)
            self.assertEqual(code, 0)
            self.assertEqual(report["changed"], ["a.md"])
            self.assertEqual(report["unresolved"], {"a.md": [ph("TEAM_ID")]})

    def test_missing_toml_bad_toml_and_not_a_repo_exit_3(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": None, "a.md": "x"})
            self.assertEqual(run_apply(root, "--root", str(root))[0], 3)
            (root / "skill_router.toml").write_text("[[[")
            git(root, "add", "-A")
            self.assertEqual(run_apply(root, "--root", str(root))[0], 3)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run_apply(tmp, "--root", tmp)[0], 3)

    def test_wrong_table_shape_exit_3(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": 'project = "x"\n'})
            self.assertEqual(run_apply(root, "--root", str(root))[0], 3)


class NoTomllibTests(unittest.TestCase):
    def test_apply_without_tomllib_exits_2_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": toml_text(name="N"), "a.md": ph("PROJECT_NAME")})
            before = snapshot(root)
            with mock.patch.dict(sys.modules, {"tomllib": None}):
                code, _, err = run_apply(root, "--root", str(root))
            self.assertEqual(code, 2)
            self.assertIn("tomllib", err)
            self.assertEqual(snapshot(root), before)


if __name__ == "__main__":
    unittest.main()
