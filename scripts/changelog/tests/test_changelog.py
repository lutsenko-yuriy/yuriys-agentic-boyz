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
from scripts.onboard.tests import template_only

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "changelog" / "changelog.py"

UNMARKED_INTRO = "# Changelog\n\nIntro.\n\n---\n\n"
INTRO = "# Changelog\n\nIntro.\n\n%s\n\n---\n\n" % changelog.MARKER
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

    def test_grandfathered_numbered_headings(self):
        for heading in ["## [1.2.0] — 2026-01-02", "## [1.2.0] - 2026-01-02", "## [1.2.0] – 2026-01-02", "## [1.2.0]",
                        "## [1.2] — 2026-01-02", "## [1.0]", "## [1.0.0-beta.1] — 2026-01-02",
                        "## [1.0.0-rc.1+build.5] - 2026-01-02", "## [0.1.0] — 2026-03-??", "## [0.1.0] — 2026-??-??",
                        "## [0.0.5] - 2014-12-13 [YANKED]", "## [1.2.0] — 2026-01-02 (PR #5) [YANKED]"]:
            self.assertEqual([], errors(doc(released="\n%s\n- x\n" % heading)), heading)

    def test_numbered_heading_format(self):
        for heading in ["## [v1.2.0] — 2026-01-02", "## [1] — 2026-01-02", "## [1.2.0] 2026-01-02",
                        "## [1.2.0] — 26-01-02", "## [1.2.0] — 2026-1-2", "## [1.2.0] — soon", "## [next]",
                        "## [1.2.0] — 2026-01-02 [yanked]", "## [1.2.0] — 2026-01-02 YANKED"]:
            found = errors(doc(released="\n%s\n- x\n" % heading))
            self.assertEqual(1, len(found), heading)
            self.assertIn("heading", found[0], heading)

    def test_legacy_heading_suffix_is_accepted(self):
        self.assertEqual([], errors(doc(released="\n## [1.2.0] — 2026-01-02 (PR #5 merged)\n- x\n")))

    def test_unreleased_must_be_single_and_on_top(self):
        released = "\n## [1.0.0] — 2026-01-02\n- x\n"
        self.assertTrue(errors(INTRO + released + "## [Unreleased]\n- #1: x [meta]\n"))
        self.assertTrue(errors(doc("- #1: x [meta]") + "## [Unreleased]\n"))

    def test_unreleased_heading_variants(self):
        for heading in ["## [unreleased]", "## [Unreleased] — pending", "## Unreleased", "## UNRELEASED", "##  [Unreleased]"]:
            found = errors(INTRO + heading + "\n- #1: x [meta]\n")
            self.assertEqual(1, len(found), (heading, found))
            self.assertIn("must be exactly '## [Unreleased]'", found[0], heading)

    def test_html_comments_are_ignored(self):
        self.assertEqual([], errors(doc("<!-- a note\n[bogus] -->", "- #1: x [meta]")))

    def test_no_unreleased_section_is_fine(self):
        self.assertEqual([], errors(INTRO + "## [1.0.0] — 2026-01-02\n- anything\n"))


class FormatMarkerTest(unittest.TestCase):
    LEGACY = UNMARKED_INTRO + "## [Unreleased]\n- [user] old style\n\n## [0.1.0] - 2026-03-??\n- x\n"

    def test_marker_text(self):
        self.assertEqual("<!-- changelog-format: yab-1 -->", changelog.MARKER)

    def test_unmarked_changelog_is_not_linted(self):
        self.assertIsNone(changelog.format_of(self.LEGACY))
        self.assertEqual([], errors(self.LEGACY))

    def test_marker_opts_in(self):
        marked = self.LEGACY.replace("Intro.\n", "Intro.\n\n%s\n" % changelog.MARKER)
        self.assertEqual("yab-1", changelog.format_of(marked))
        self.assertTrue(errors(marked))

    def test_marker_must_be_its_own_line(self):
        self.assertIsNone(changelog.format_of("<!-- note\n%s inline -->\n" % changelog.MARKER))

    def test_marker_with_crlf_line_endings(self):
        crlf = INTRO.replace("\n", "\r\n") + "## [Unreleased]\r\n- #1: no tag\r\n"
        self.assertEqual("yab-1", changelog.format_of(crlf))
        self.assertEqual(1, len(errors(crlf)))

    def test_marker_after_a_bom(self):
        bom = "\ufeff" + changelog.MARKER + "\n\n---\n\n## [Unreleased]\n- #1: no tag\n"
        self.assertEqual("yab-1", changelog.format_of(bom))
        self.assertEqual(1, len(errors(bom)))

    def test_marker_with_surrounding_whitespace(self):
        indented = INTRO.replace(changelog.MARKER, "  \t" + changelog.MARKER + " \t")
        self.assertEqual("yab-1", changelog.format_of(indented))
        self.assertEqual(1, len(errors(indented + "## [Unreleased]\n- #1: no tag\n")))

    def test_marker_below_the_intro_is_not_an_opt_in(self):
        for where in ["## [Unreleased]\n%s\n- x\n", "```\n%s\n```\n", "\n---\n\n%s\n"]:
            text = UNMARKED_INTRO + where % changelog.MARKER
            self.assertIsNone(changelog.format_of(text), where)
            self.assertEqual([], errors(text), where)

    def test_second_marker_is_a_finding(self):
        base = INTRO.count("\n")
        for text, line in [
            (INTRO.replace(changelog.MARKER, changelog.MARKER + "\n" + changelog.MARKER), 6),
            (doc("- #1: x [meta]") + changelog.MARKER.replace("yab-1", "yab-9") + "\n", None),
            (INTRO + "## [1.0.0] — 2026-01-02\n```\n  %s\n```\n" % changelog.MARKER, base + 3),
        ]:
            found = changelog.lint(text)
            self.assertEqual(1, len(found), (text, found))
            self.assertIn("second", found[0]["error"])
            self.assertEqual(changelog.FORMAT, changelog.format_of(text))
            if line:
                self.assertEqual(line, found[0]["line"])

    def test_unknown_format_is_a_finding(self):
        found = changelog.lint(INTRO.replace("yab-1", "yab-9"))
        self.assertEqual(1, len(found))
        self.assertIn("yab-9", found[0]["error"])


@template_only  # an onboarded project's CHANGELOG is its own, linted by the CI step instead
class RealFilesTest(unittest.TestCase):
    def test_project_changelog_passes(self):
        self.assertEqual([], changelog.lint((ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")))

    def test_footer_examples_are_not_literal_headings(self):
        # /ship must never take an example inside the footer comment for the real ## [Unreleased] heading.
        text = (ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
        hidden = [raw for raw, shown in zip(text.splitlines(), changelog._blank_comments(text)) if raw != shown]
        self.assertTrue(hidden)
        self.assertEqual([], [ln for ln in hidden if ln.startswith(("#", "- "))])

    def test_emptied_template_changelog_passes(self):
        text = (ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
        emptied = onboard._empty_changelog(text)
        self.assertEqual(changelog.FORMAT, changelog.format_of(emptied))  # new projects start opted in
        self.assertEqual([], changelog.lint(emptied))


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

    def test_unmarked_lint_prints_a_one_line_notice(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = changelog.main(["lint", self.write(FormatMarkerTest.LEGACY)])
        self.assertEqual(0, code)
        self.assertEqual(1, len(out.getvalue().strip().splitlines()))
        self.assertIn(changelog.MARKER, json.loads(out.getvalue())["notice"])

    def test_unmarked_unreleased_and_propose_carry_the_notice(self):
        path = self.write(UNMARKED_INTRO + "## [Unreleased]\n- #1: x [user] PATCH\n")
        code, out = self.run_main("unreleased", path)
        self.assertEqual(0, code)
        self.assertIn(changelog.MARKER, out["notice"])
        code, out = self.run_main("propose", path, "--current", "1.0.0")
        self.assertEqual((0, "1.0.1"), (code, out["version"]))
        self.assertIn("notice", out)
        code, out = self.run_main("unreleased", self.write(FormatMarkerTest.LEGACY))
        self.assertEqual(1, code)
        self.assertIn("notice", out)

    def test_unknown_format_refuses_unreleased_and_propose(self):
        path = self.write(doc("- #1: x [user] PATCH").replace("yab-1", "yab-9"))
        lint_error = changelog.lint(Path(path).read_text(encoding="utf-8"))[0]["error"]
        for argv in (["unreleased", path], ["propose", path, "--current", "1.0.0"]):
            code, out = self.run_main(*argv)
            self.assertEqual(1, code, argv)
            self.assertEqual(lint_error, out["error"], argv)
            self.assertNotIn("notice", out, argv)

    def test_marked_output_has_no_notice(self):
        self.assertNotIn("notice", self.run_main("unreleased", self.write(doc("- #1: x [meta]")))[1])

    def test_missing_file(self):
        code, out = self.run_main("lint", "/nonexistent/CHANGELOG.md")
        self.assertEqual(1, code)
        self.assertIn("error", out)

    def test_runs_as_a_script(self):
        proc = subprocess.run([sys.executable, "-W", "error", str(SCRIPT), "lint", self.write(doc("- #1: x [meta]"))],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
