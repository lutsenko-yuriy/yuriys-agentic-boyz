import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from scripts.onboard import onboard

try:
    import tomllib  # noqa: F401

    HAS_TOMLLIB = True
except ImportError:
    HAS_TOMLLIB = False

needs_toml = unittest.skipUnless(HAS_TOMLLIB, "tomllib needs Python 3.11+")


class PrefixTests(unittest.TestCase):
    def test_rejects_invalid(self):
        for bad in ["", "N/A", "n/a", "NA", "na", "A B", "1AB", "A", "ABCDEFGHIJK", "  "]:
            self.assertFalse(onboard.valid_prefix(bad), bad)

    def test_accepts_valid(self):
        for good in ["HAB", "CheL", "GH", "HL", "A1", "ABCDEFGHIJ"]:
            self.assertTrue(onboard.valid_prefix(good), good)

    def test_defaults(self):
        self.assertEqual(onboard.default_prefix("Habit Loop"), "HL")
        self.assertEqual(onboard.default_prefix("CheckLister"), "CL")
        self.assertEqual(onboard.default_prefix("mordovorot"), "MOR")

    def test_defaults_are_always_valid_or_empty(self):
        self.assertEqual(onboard.default_prefix("2048 Game"), "GAM")
        self.assertEqual(onboard.default_prefix("X"), "")
        self.assertEqual(onboard.default_prefix(" ".join("abcdefghijkl")), "ABCDEFGHIJ")


class ProbeTests(unittest.TestCase):
    def test_reports_env_names_never_values(self):
        env = {"OPENAI_API_KEY": "sekrit-value", "HOME": "/x", "CLAUDE_CODE_MESSAGING_TOKEN": "t", "AWS_SECRET": "s"}
        with mock.patch.dict("os.environ", env, clear=True):
            data = onboard.probe(run_tools=False)
        self.assertEqual(data["env_vars_set"], ["AWS_SECRET", "OPENAI_API_KEY"])
        self.assertNotIn("sekrit-value", json.dumps(data))

    def test_tool_failures_are_independent_and_keys_stable(self):
        def fake_run(cmd, **kw):
            if cmd[0] == "ollama":
                raise OSError("daemon down")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with mock.patch("shutil.which", return_value="/bin/x"), mock.patch("subprocess.run", side_effect=fake_run):
            data = onboard.probe()
        self.assertIsNone(data["ollama_models"])
        self.assertTrue(data["gh_authenticated"])

    def test_tool_keys_present_when_tools_absent(self):
        with mock.patch("shutil.which", return_value=None):
            data = onboard.probe()
        self.assertIsNone(data["ollama_models"])
        self.assertIsNone(data["gh_authenticated"])

    def test_toolchains_via_which_without_executing(self):
        with mock.patch("shutil.which", side_effect=lambda n: "/bin/" + n if n == "git" else None), mock.patch(
            "subprocess.run", side_effect=AssertionError("must not execute")
        ):
            data = onboard.probe(run_tools=False)
        self.assertEqual(data["toolchains"]["git"], True)
        self.assertEqual(data["toolchains"]["flutter"], False)

    def test_python_versions_with_tomllib_from_names(self):
        with mock.patch("shutil.which", side_effect=lambda n: "/bin/" + n if n in ("python3.12", "python3.10") else None):
            data = onboard.probe(run_tools=False)
        self.assertEqual(data["pythons_with_tomllib"], ["python3.12"])


class LoadTomlTests(unittest.TestCase):
    def test_missing_tomllib_fails_loudly_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.toml"
            p.write_text("a = 1\n")
            with mock.patch.dict(sys.modules, {"tomllib": None}):
                with self.assertRaises(SystemExit) as cm, mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                    onboard.load_toml(p)
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("python3.12", err.getvalue())

    def test_probe_cli_works_without_tomllib(self):
        with mock.patch.dict(sys.modules, {"tomllib": None}), mock.patch(
            "shutil.which", return_value=None
        ), redirect_stdout(io.StringIO()) as out:
            code = onboard.main(["probe"])
        self.assertEqual(code, 0)
        json.loads(out.getvalue())


GOOD_TOML = """[providers]
pm = "linear"
vcs = "github"

[project]
name = "Habit Loop"
description = "d"
issue_prefix = "HL"
"""
GOOD_ARTIFACT = "# Doc\n"
GOOD_TECH = "## Languages\n\n| Language | Version |\n|---|---|\n| Dart | 3.6 |\n\n## Platforms\n"
GOOD_STYLE = "# Style\n\n## Base standard\n\nDart: Effective Dart.\n\n## Other\n"


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def make_repo(tmp, files=None):
    root = Path(tmp)
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    base = {
        "skill_router.toml": GOOD_TOML,
        "docs/TECH_STACK.md": GOOD_TECH,
        "docs/CODE_STYLE.md": GOOD_STYLE,
        "docs/CONSTRAINTS.md": GOOD_ARTIFACT,
    }
    base.update(files or {})
    for rel, content in base.items():
        if content is None:
            continue
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    return root


def run_check(root):
    return onboard.check(Path(root))


@needs_toml
class CheckTests(unittest.TestCase):
    def check(self, files=None):
        with tempfile.TemporaryDirectory() as tmp:
            return run_check(make_repo(tmp, files))

    def msgs(self, result, key="errors"):
        return " | ".join(result[key])

    def test_clean_repo(self):
        r = self.check()
        self.assertTrue(r["ok"], r)
        self.assertFalse(r["template_mode"])

    def test_remaining_placeholders_listed_per_file(self):
        r = self.check({"AGENTS.md": "x {{PROJECT_NAME}} y {{STACK}}\n"})
        self.assertFalse(r["ok"])
        self.assertEqual(sorted(r["placeholders"]["AGENTS.md"]), ["{{PROJECT_NAME}}", "{{STACK}}"])

    def test_untracked_files_ignored_for_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp)
            (root / "scratch.md").write_text("{{STACK}}")
            self.assertEqual(run_check(root)["placeholders"], {})

    def test_missing_artifact(self):
        r = self.check({"docs/CONSTRAINTS.md": None})
        self.assertFalse(r["ok"])
        self.assertIn("docs/CONSTRAINTS.md", self.msgs(r))

    def test_template_marker_artifact(self):
        r = self.check({"docs/TECH_STACK.md": TEMPLATE_DOC})
        self.assertFalse(r["ok"])
        self.assertIn("template", self.msgs(r))

    def test_empty_project_field(self):
        r = self.check({"skill_router.toml": GOOD_TOML.replace('description = "d"', 'description = ""')})
        self.assertFalse(r["ok"])
        self.assertIn("project.description", self.msgs(r))

    def test_missing_pm(self):
        r = self.check({"skill_router.toml": GOOD_TOML.replace('pm = "linear"\n', "")})
        self.assertIn("providers.pm", self.msgs(r))

    def test_invalid_prefix(self):
        for bad in ["N/A", "NA", "A B", ""]:
            r = self.check({"skill_router.toml": GOOD_TOML.replace('"HL"', '"%s"' % bad)})
            self.assertFalse(r["ok"], bad)

    def test_base_standard_mismatch(self):
        r = self.check({"docs/TECH_STACK.md": GOOD_TECH.replace("| Dart | 3.6 |", "| Dart | 3.6 |\n| Python | 3.12 |")})
        self.assertFalse(r["ok"])
        self.assertIn("Python", self.msgs(r))

    def test_note_filename_warning_only(self):
        r = self.check({"docs/knowledge/notes/1.md": "x", "docs/knowledge/notes/HL-2.md": "x", "docs/knowledge/notes/INDEX.md": "x"})
        self.assertTrue(r["ok"])
        self.assertIn("1.md", self.msgs(r, "warnings"))
        self.assertNotIn("HL-2.md", self.msgs(r, "warnings"))
        self.assertNotIn("INDEX.md", self.msgs(r, "warnings"))

    def test_template_mode_sentinel(self):
        r = self.check({".yab-template": ""})
        self.assertTrue(r["template_mode"])

    def test_template_mode_tolerates_template_state(self):
        r = self.check({
            ".yab-template": "",
            "AGENTS.md": "{{PROJECT_NAME}}",
            "docs/TECH_STACK.md": TEMPLATE_DOC,
            "skill_router.toml": "[providers]\n",
        })
        self.assertTrue(r["ok"], r)

    def test_template_mode_still_requires_artifacts(self):
        r = self.check({".yab-template": "", "docs/CONSTRAINTS.md": None})
        self.assertFalse(r["ok"])

    def test_only_known_placeholders_count(self):
        r = self.check({
            "gen.py": 'x = f".//{{{SVG_NS}}}g"\n',
            "flow.py": "appId: ${{APP_ID}}\n",
            "README.md": "{{NOT_OURS}}\n",
        })
        self.assertTrue(r["ok"], r)

    def test_history_files_skipped(self):
        r = self.check({"docs/knowledge/notes/HL-1.md": "`{{ISSUE_PREFIX}}-XX`", "docs/CHANGELOG.md": "{{STACK}}"})
        self.assertTrue(r["ok"], r)

    def test_symlinks_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "secret.md").write_text("{{STACK}}")
            root = make_repo(tmp)
            (root / "link.md").symlink_to(Path(outside) / "secret.md")
            git(root, "add", "-A")
            self.assertTrue(run_check(root)["ok"])

    def test_language_match_is_whole_word(self):
        tech = GOOD_TECH.replace("| Dart | 3.6 |", "| Go | 1.22 |\n| Java | 17 |")
        style = "## Base standard\n\nGoogle Shell Style Guide; JavaScript standard.\n"
        r = self.check({"docs/TECH_STACK.md": tech, "docs/CODE_STYLE.md": style})
        self.assertIn("Go", self.msgs(r))
        self.assertIn("Java", self.msgs(r))

    def test_language_alternatives_each_required(self):
        tech = GOOD_TECH.replace("| Dart | 3.6 |", "| TypeScript / JavaScript | 5 |")
        style = "## Base standard\n\nTypeScript and JavaScript: ESLint.\n"
        self.assertTrue(self.check({"docs/TECH_STACK.md": tech, "docs/CODE_STYLE.md": style})["ok"])

    def test_missing_languages_section(self):
        r = self.check({"docs/TECH_STACK.md": "# Stack\n"})
        self.assertIn("Languages", self.msgs(r))

    def test_unreadable_artifact_is_reported_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp)
            (root / "docs/CONSTRAINTS.md").write_bytes(b"\xff\xfe bad")
            r = run_check(root)
        self.assertIn("docs/CONSTRAINTS.md", self.msgs(r))

    def test_cli_exit_codes_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp)
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(onboard.main(["--root", str(root), "check"]), 0)
            self.assertTrue(json.loads(out.getvalue())["ok"])
            (root / "AGENTS.md").write_text("{{STACK}}")
            git(root, "add", "-A")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(onboard.main(["--root", str(root), "check"]), 1)

    def test_cli_errors_exit_3_not_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": "[broken\n"})
            with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                self.assertEqual(onboard.main(["--root", str(root), "check"]), 3)
            self.assertIn("onboard:", err.getvalue())

    def test_not_a_git_repo_exit_3(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()), mock.patch(
            "sys.stderr", new_callable=io.StringIO
        ):
            self.assertEqual(onboard.main(["--root", tmp, "check"]), 3)

    def test_default_root_is_repo_toplevel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp)
            sub = root / "docs"
            with mock.patch("os.getcwd", return_value=str(sub)), redirect_stdout(io.StringIO()) as out:
                code = onboard.main(["check"])
            self.assertEqual(code, 0, out.getvalue())


TEMPLATE_DOC = "<!-- yab:template -->\n# T\n"


@needs_toml
class MarkTests(unittest.TestCase):
    def test_mark_writes_marker_in_common_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(onboard.main(["--root", str(root), "mark"]), 0)
            marker = root / ".git" / "yab" / "onboarded"
            self.assertTrue(marker.is_file())
            self.assertIn("sha=" + git(root, "rev-parse", "HEAD").strip(), marker.read_text())
            self.assertEqual(git(root, "status", "--porcelain"), "")

    def test_mark_refuses_when_not_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"AGENTS.md": "{{STACK}}"})
            with redirect_stdout(io.StringIO()):
                self.assertEqual(onboard.main(["--root", str(root), "mark"]), 1)
            self.assertFalse((root / ".git" / "yab" / "onboarded").exists())

    def test_mark_force_from_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"AGENTS.md": "{{STACK}}"})
            with redirect_stdout(io.StringIO()), mock.patch("sys.stdin.isatty", return_value=True):
                self.assertEqual(onboard.main(["--root", str(root), "mark", "--force"]), 0)
            self.assertTrue((root / ".git" / "yab" / "onboarded").exists())

    def test_mark_force_refused_without_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"AGENTS.md": "{{STACK}}"})
            with redirect_stdout(io.StringIO()), mock.patch("sys.stdin.isatty", return_value=False), mock.patch(
                "sys.stderr", new_callable=io.StringIO
            ):
                self.assertEqual(onboard.main(["--root", str(root), "mark", "--force"]), 1)
            self.assertFalse((root / ".git" / "yab" / "onboarded").exists())

    def test_mark_outside_git_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()), mock.patch(
            "sys.stdin.isatty", return_value=True
        ), mock.patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(onboard.main(["--root", tmp, "mark", "--force"]), 3)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_mark_unborn_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            with redirect_stdout(io.StringIO()), mock.patch("sys.stdin.isatty", return_value=True):
                onboard.main(["--root", str(root), "mark", "--force"])
            self.assertIn("sha=unknown", (root / ".git" / "yab" / "onboarded").read_text())

    def test_marker_visible_from_worktree(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as wt:
            root = make_repo(tmp)
            with redirect_stdout(io.StringIO()):
                onboard.main(["--root", str(root), "mark"])
            wtp = Path(wt) / "w"
            git(root, "worktree", "add", "-q", str(wtp), "-b", "other")
            common = Path(git(wtp, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
            self.assertTrue((common / "yab" / "onboarded").is_file())
            self.assertEqual(onboard.marker_path(wtp), root.resolve() / ".git" / "yab" / "onboarded")
