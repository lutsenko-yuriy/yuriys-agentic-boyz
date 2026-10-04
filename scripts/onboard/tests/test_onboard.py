import io
import json
import os
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
project_id = "p1"
"""
GOOD_ARTIFACT = "# Doc\n"
GOOD_TECH = "## Languages\n\n| Language | Version |\n|---|---|\n| Dart | 3.6 |\n\n## Platforms\n"
GOOD_STYLE = "# Style\n\n## Base standard\n\nDart: Effective Dart.\n\n## Other\n"


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


YAB_ORIGIN = "https://github.com/lutsenko-yuriy/yuriys-agentic-boyz.git"
YAB_SENTINEL = "repo=lutsenko-yuriy/yuriys-agentic-boyz\n"


def make_repo(tmp, files=None, origin=None):
    root = Path(tmp)
    git(root, "init", "-q")
    if origin:
        git(root, "remote", "add", "origin", origin)
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
    def check(self, files=None, origin=None):
        with tempfile.TemporaryDirectory() as tmp:
            return run_check(make_repo(tmp, files, origin))

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

    def test_pm_must_be_a_router_provider(self):
        for pm in ["jira", "github_issues", "files"]:
            with self.subTest(pm):
                r = self.check({"skill_router.toml": GOOD_TOML.replace('pm = "linear"', 'pm = "%s"' % pm)})
                self.assertIn("providers.pm %r must be one of" % pm, self.msgs(r))

    def test_linear_requires_project_id(self):
        r = self.check({"skill_router.toml": GOOD_TOML.replace('project_id = "p1"\n', "")})
        self.assertIn("project.project_id is empty", self.msgs(r))
        r = self.check({"skill_router.toml": GOOD_TOML.replace('project_id = "p1"\n', "").replace('"linear"', '"github"')})
        self.assertNotIn("project.project_id", self.msgs(r))

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
        r = self.check({".yab-template": YAB_SENTINEL}, origin=YAB_ORIGIN)
        self.assertTrue(r["template_mode"])

    def test_template_origin_must_match_exactly(self):
        for origin in [
            "https://github.com/lutsenko-yuriy/yuriys-agentic-boyz-playground.git",
            "https://gitlab.com/mirror/lutsenko-yuriy/yuriys-agentic-boyz.git",
            "git@github.com:someone/yuriys-agentic-boyz.git",
            "file://github.com/lutsenko-yuriy/yuriys-agentic-boyz",
            "github.com/lutsenko-yuriy/yuriys-agentic-boyz",
            "https://github.com/group/lutsenko-yuriy/yuriys-agentic-boyz",
            "alias:x@github.com:lutsenko-yuriy/yuriys-agentic-boyz",
            "ext::git@github.com:lutsenko-yuriy/yuriys-agentic-boyz",
        ]:
            r = self.check({".yab-template": YAB_SENTINEL}, origin=origin)
            self.assertFalse(r["template_mode"], origin)

    def test_local_remotes_have_no_network_id(self):
        for local in ["file:///srv/git/yuriys-agentic-boyz", "C:/repo/yuriys-agentic-boyz", "../yuriys-agentic-boyz"]:
            self.assertIsNone(onboard._remote_id(local), local)

    def test_template_origin_forms_accepted(self):
        for origin in [
            "git@github.com:lutsenko-yuriy/yuriys-agentic-boyz.git",
            "https://github.com/Lutsenko-Yuriy/Yuriys-Agentic-Boyz",
            "ssh://git@github.com/lutsenko-yuriy/yuriys-agentic-boyz.git",
            "ssh://git@ssh.github.com:443/lutsenko-yuriy/yuriys-agentic-boyz.git",
            "HTTPS://user@github.com:8443/lutsenko-yuriy/yuriys-agentic-boyz.git//",
            "git@github.com:/lutsenko-yuriy/yuriys-agentic-boyz",
            "https://github.com/lutsenko-yuriy/yuriys-agentic-boyz?x=1",
            "github.com:lutsenko-yuriy/yuriys-agentic-boyz",
            "git+ssh://git@GitHub.com/lutsenko-yuriy/yuriys-agentic-boyz.GIT",
            "ssh+git://git@github.com/lutsenko-yuriy/yuriys-agentic-boyz",
        ]:
            self.assertTrue(self.check({".yab-template": YAB_SENTINEL}, origin=origin)["template_mode"], origin)

    def test_yab_as_upstream_only_is_not_template_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {".yab-template": YAB_SENTINEL, "AGENTS.md": "{{PROJECT_NAME}}"},
                             "https://github.com/lutsenko-yuriy/my-new-app.git")
            git(root, "remote", "add", "upstream", YAB_ORIGIN)
            r = run_check(root)
        self.assertFalse(r["template_mode"])
        self.assertFalse(r["ok"])

    def test_sentinel_without_origin_is_reported(self):
        r = self.check({".yab-template": YAB_SENTINEL})
        self.assertFalse(r["template_mode"])
        self.assertIn(".yab-template", self.msgs(r))

    def test_sentinel_repo_is_case_insensitive(self):
        r = self.check({".yab-template": YAB_SENTINEL.upper().replace("REPO=", "repo=")}, origin=YAB_ORIGIN)
        self.assertTrue(r["template_mode"])

    def test_empty_remote_url_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {".yab-template": YAB_SENTINEL})
            git(root, "config", "remote.origin.url", "")
            self.assertFalse(run_check(root)["template_mode"])

    def test_sentinel_content_must_name_yab_exactly(self):
        for content in ["", "repo=lutsenko-yuriy/yuriys-agentic-boyz-x\n"]:
            r = self.check({".yab-template": content}, origin=YAB_ORIGIN)
            self.assertFalse(r["template_mode"], content)

    def test_inherited_sentinel_is_not_template_mode(self):
        r = self.check({".yab-template": YAB_SENTINEL, "AGENTS.md": "{{PROJECT_NAME}}"},
                       origin="git@github.com:someone/new-app.git")
        self.assertFalse(r["template_mode"])
        self.assertFalse(r["ok"])
        self.assertIn(".yab-template", self.msgs(r))

    def test_template_mode_tolerates_template_state(self):
        r = self.check({
            ".yab-template": YAB_SENTINEL,
            "AGENTS.md": "{{PROJECT_NAME}}",
            "docs/TECH_STACK.md": TEMPLATE_DOC,
            "skill_router.toml": "[providers]\n",
        }, origin=YAB_ORIGIN)
        self.assertTrue(r["ok"], r)

    def test_template_mode_still_requires_artifacts(self):
        r = self.check({".yab-template": YAB_SENTINEL, "docs/CONSTRAINTS.md": None}, origin=YAB_ORIGIN)
        self.assertTrue(r["template_mode"])
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

    def test_knowledge_templates_and_readmes_still_scanned(self):
        r = self.check({
            "docs/knowledge/notes/TEMPLATE.md": "{{ISSUE_PREFIX}}-XX",
            "docs/knowledge/decisions/README.md": "{{ISSUE_PREFIX}}",
            "docs/CHANGELOG.md.bak": "{{STACK}}",
        })
        self.assertEqual(sorted(r["placeholders"]),
                         ["docs/CHANGELOG.md.bak", "docs/knowledge/decisions/README.md",
                          "docs/knowledge/notes/TEMPLATE.md"])

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
        r = self.check({"docs/TECH_STACK.md": tech, "docs/CODE_STYLE.md": "## Base standard\n\nTypeScript: ESLint.\n"})
        self.assertIn("language JavaScript", self.msgs(r))

    def test_language_names_parsed_fully(self):
        tech = ("## Languages\n\n| Note: one row per language |\n| Versions are minimums |\n\n| Language | Version |\n|:---|---:|\n"
                "| 🐍 Python | 3 |\n| .NET | 8 |\n| Visual Basic | 6 |\n| 3.12 | x |\n")
        self.assertEqual(onboard._languages(tech), ["Python", ".NET", "Visual Basic"])

    def test_version_notations_stripped_from_names(self):
        tech = ("## Languages\n\n| Language | Version |\n|---|---|\n| Dart ^3.6.0 | |\n| Python >=3.11 | |\n"
                "| Kotlin 2.0+ | |\n| Python3.12 | |\n| Node v20 LTS | |\n| 3.x | |\n| v20 | |\n| LTS | |\n"
                "| Python >= 3.11 | |\n| Elixir ~> 1.16 | |\n| Ruby ≥ 3.3 | |\n")
        self.assertEqual(onboard._languages(tech), ["Dart", "Python", "Kotlin", "Python", "Node", "Python", "Elixir", "Ruby"])

    def test_version_suffix_counts_as_mention(self):
        tech = GOOD_TECH.replace("| Dart | 3.6 |", "| C++ | 17 |\n| Python | 3 |")
        style = "## Base standard\n\nC++17 Core Guidelines. Python3: PEP 8.\n"
        self.assertTrue(self.check({"docs/TECH_STACK.md": tech, "docs/CODE_STYLE.md": style})["ok"])

    def test_language_cell_markup_and_qualifiers(self):
        tech = GOOD_TECH.replace("| Dart | 3.6 |", "| Dart (Flutter) | 3.6 |\n| **Python** 3.12 | x |")
        style = "## Base standard\n\nDart: Effective Dart. Python: PEP 8.\n"
        self.assertTrue(self.check({"docs/TECH_STACK.md": tech, "docs/CODE_STYLE.md": style})["ok"])

    def test_c_not_covered_by_cpp_or_objective_c(self):
        tech = GOOD_TECH.replace("| Dart | 3.6 |", "| C | 17 |")
        style = "## Base standard\n\nC++ Core Guidelines; Objective-C conventions.\n"
        self.assertIn("language C", self.msgs(self.check({"docs/TECH_STACK.md": tech, "docs/CODE_STYLE.md": style})))

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

    def test_wrong_toml_shape_exit_3_naming_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"skill_router.toml": 'project = "x"\nproviders = 1\n'})
            with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                self.assertEqual(onboard.main(["--root", str(root), "check"]), 3)
            self.assertIn("skill_router.toml", err.getvalue())

    def test_non_utf8_tracked_filename_does_not_abort(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp)
            try:
                with open(os.path.join(os.fsencode(str(root)), b"bad\xff.md"), "wb") as f:
                    f.write(b"x")
            except OSError:
                self.skipTest("filesystem rejects non-UTF-8 names")
            git(root, "add", "-A")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(onboard.main(["--root", str(root), "check"]), 0)

    def test_root_spelled_differently_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp)
            spelled = str(root) + "/docs/.."
            with redirect_stdout(io.StringIO()):
                self.assertEqual(onboard.main(["--root", spelled, "check"]), 0)
            if os.path.exists(str(root).swapcase()):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(onboard.main(["--root", str(root).swapcase(), "check"]), 0)

    def test_usage_error_exit_3(self):
        with mock.patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(onboard.main(["chek"]), 3)
            self.assertEqual(onboard.main([]), 3)

    def test_root_inside_enclosing_repo_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            outer = make_repo(tmp)
            inner = outer / "plain"
            inner.mkdir()
            with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", new_callable=io.StringIO), mock.patch(
                "sys.stdin.isatty", return_value=True
            ):
                self.assertEqual(onboard.main(["--root", str(inner), "mark", "--force"]), 3)
            self.assertFalse((outer / ".git" / "yab").exists())

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

    def test_mark_force_with_closed_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp)
            with redirect_stdout(io.StringIO()), mock.patch("sys.stdin", None), mock.patch(
                "sys.stderr", new_callable=io.StringIO
            ):
                self.assertEqual(onboard.main(["--root", str(root), "mark", "--force"]), 1)

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
