import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.changelog import changelog
from scripts.onboard import onboard

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "changelog" / "changelog.py"

INTRO = "# Changelog\n\nIntro.\n\n---\n\n"
FOOTER = "\n---\n\n<!-- ## [Unreleased]\n- not linted [bogus] -->\n"


def doc(*lines, released=""):
    return INTRO + "## [Unreleased]\n" + "".join(ln + "\n" for ln in lines) + released + FOOTER


def errors(text):
    return [f["error"] for f in changelog.lint(text)]


class LineGrammarTest(unittest.TestCase):
    def test_accepted(self):
        for line in [
            "- #1: summary (PR #2) [meta]",
            "- #1: summary [wip]",
            "- HAB-278 WU1: onboard.py probe [wip]",
            "- #42: asks for tools ([tools] in skill_router.toml; none is recorded) (PR #43) [meta]",
            "- #1: summary (PR #2) [user] MINOR",
            "- #1: summary (PR #2) [app] PATCH",
            "- #1: summary (PR #2) [user] [non-user] MAJOR",
            "- #1: summary (PR #2) [user] MINOR flags: dark_mode",
            "- #1: summary (PR #2) [app] PATCH flags: a.b, c-d,e_1",
            "- #1: summary [test] [ci]",
        ]:
            self.assertEqual([], errors(doc(line)), line)

    def test_rejected(self):
        for line, needle in [
            ("- #1: summary (PR #2)", "tag"),
            ("- summary [meta]", "ID"),
            ("- #1: summary [bogus]", "bogus"),
            ("- #1: summary [non-user]", "classification"),
            ("- #1: summary [meta] [meta]", "twice"),
            ("- #1: summary [user]", "mark"),
            ("- #1: summary [app] flags: x", "mark"),
            ("- #1: summary [meta] MINOR", "MINOR"),
            ("- #1: summary [user] minor", "minor"),
            ("- #1: summary [user] [MINOR]", "MINOR"),
            ("- #1: summary [meta] flags: x", "mark"),
            ("- #1: summary [user] MINOR flags: ", "flag"),
            ("- #1: summary [user] MINOR flags: bad name", "bad name"),
            ("- #1: summary [user] MINOR flags: a,,b", "flag"),
            ("free text", "unexpected"),
        ]:
            found = errors(doc(line))
            self.assertEqual(1, len(found), (line, found))
            self.assertIn(needle, found[0], line)

    def test_finding_has_file_line_number(self):
        text = doc("- #1: ok [meta]", "- #2: no tag")
        self.assertEqual([INTRO.count("\n") + 3], [f["line"] for f in changelog.lint(text)])

    def test_subheadings_rules_and_blank_lines_allowed(self):
        self.assertEqual([], errors(doc("### Added / Changed / Fixed", "- #1: x [meta]", "", "- #2: y [ci]")))


class SectionTest(unittest.TestCase):
    def test_numbered_lines_are_not_linted(self):
        released = "\n## [1.2.0] — 2026-01-02\n\n- [user] old style line\nfree text\n"
        self.assertEqual([], errors(doc("- #1: x [meta]", released=released)))

    def test_numbered_heading_format(self):
        for heading in ["## [1.2] — 2026-01-02", "## [1.2.0] - 2026-01-02", "## [1.2.0]", "## [v1.2.0] — 2026-01-02"]:
            found = errors(doc(released="\n%s\n- x\n" % heading))
            self.assertEqual(1, len(found), heading)
            self.assertIn("heading", found[0], heading)

    def test_legacy_heading_suffix_is_accepted(self):
        self.assertEqual([], errors(doc(released="\n## [1.2.0] — 2026-01-02 (PR #5 merged)\n- x\n")))

    def test_unreleased_must_be_single_and_on_top(self):
        released = "\n## [1.0.0] — 2026-01-02\n- x\n"
        self.assertTrue(errors(INTRO + released + "## [Unreleased]\n- #1: x [meta]\n"))
        self.assertTrue(errors(doc("- #1: x [meta]") + "## [Unreleased]\n"))

    def test_html_comments_are_ignored(self):
        self.assertEqual([], errors(doc("<!-- a note\n[bogus] -->", "- #1: x [meta]")))

    def test_no_unreleased_section_is_fine(self):
        self.assertEqual([], errors(INTRO + "## [1.0.0] — 2026-01-02\n- anything\n"))


class RealFilesTest(unittest.TestCase):
    def test_project_changelog_passes(self):
        self.assertEqual([], changelog.lint((ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")))

    def test_emptied_template_changelog_passes(self):
        text = (ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual([], changelog.lint(onboard._empty_changelog(text)))


class UnreleasedTest(unittest.TestCase):
    TEXT = doc("- #1: a [meta]", "- #2: b (PR #3) [user] MINOR flags: f1, f2", "- #4: c [app]", "- #5: d [wip]",
               released="\n## [1.0.0] — 2026-01-02\n- #9: old [user] MAJOR\n")

    def test_app_lines_and_non_app_count(self):
        result = changelog.unreleased(self.TEXT)
        base = INTRO.count("\n") + 1
        self.assertEqual(2, result["non_app"])
        self.assertEqual([
            {"line": base + 2, "text": "- #2: b (PR #3) [user] MINOR flags: f1, f2", "tags": ["user"],
             "mark": "MINOR", "flags": ["f1", "f2"]},
            {"line": base + 3, "text": "- #4: c [app]", "tags": ["app"], "mark": None, "flags": []},
        ], result["app"])

    def test_other_findings_refuse(self):
        with self.assertRaises(changelog.ChangelogError):
            changelog.unreleased(doc("- #1: a [bogus]"))

    def test_no_unreleased_section(self):
        self.assertEqual({"app": [], "non_app": 0}, changelog.unreleased(INTRO))


class ProposeTest(unittest.TestCase):
    def test_highest_mark_wins(self):
        for marks, current, expected in [
            (["PATCH"], "1.2.3", "1.2.4"),
            (["PATCH", "MINOR"], "1.2.3", "1.3.0"),
            (["MINOR", "MAJOR", "PATCH"], "1.2.3", "2.0.0"),
            (["MINOR"], "0.0.0", "0.1.0"),
        ]:
            text = doc("- #0: m [meta]", *["- #%d: x [app] %s" % (i, m) for i, m in enumerate(marks, 1)])
            self.assertEqual(expected, changelog.propose(text, current), marks)

    def test_missing_mark_refuses(self):
        with self.assertRaises(changelog.ChangelogError) as cm:
            changelog.propose(doc("- #1: x [user] MINOR", "- #2: y [app]"), "1.0.0")
        self.assertIn("mark", str(cm.exception))

    def test_nothing_to_release_refuses(self):
        with self.assertRaises(changelog.ChangelogError):
            changelog.propose(doc("- #1: x [meta]"), "1.0.0")

    def test_bad_current_version_refuses(self):
        with self.assertRaises(changelog.ChangelogError):
            changelog.propose(doc("- #1: x [user] MINOR"), "v1.0")


class CliTest(unittest.TestCase):
    def run_main(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = changelog.main(list(argv))
        return code, json.loads(out.getvalue())

    def write(self, text):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        path = Path(d.name) / "CHANGELOG.md"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_lint(self):
        self.assertEqual((0, {"findings": []}), self.run_main("lint", self.write(doc("- #1: x [meta]"))))
        code, out = self.run_main("lint", self.write(doc("- #1: x")))
        self.assertEqual(1, code)
        self.assertEqual(1, len(out["findings"]))

    def test_unreleased(self):
        code, out = self.run_main("unreleased", self.write(doc("- #1: x [user] PATCH")))
        self.assertEqual((0, 0), (code, out["non_app"]))
        code, out = self.run_main("unreleased", self.write(doc("- #1: x [bogus]")))
        self.assertEqual(1, code)
        self.assertIn("findings", out)

    def test_propose(self):
        path = self.write(doc("- #1: x [user] MINOR"))
        self.assertEqual((0, {"version": "1.1.0"}), self.run_main("propose", path, "--current", "1.0.9"))
        code, out = self.run_main("propose", self.write(doc("- #1: x [user]")), "--current", "1.0.0")
        self.assertEqual(1, code)
        self.assertIn("error", out)

    def test_missing_file(self):
        code, out = self.run_main("lint", "/nonexistent/CHANGELOG.md")
        self.assertEqual(1, code)
        self.assertIn("error", out)

    def test_runs_as_a_script(self):
        proc = subprocess.run([sys.executable, "-W", "error", str(SCRIPT), "lint", str(ROOT / "docs" / "CHANGELOG.md")],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
