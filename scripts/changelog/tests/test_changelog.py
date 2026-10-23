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

    def test_shipped_changelog_is_empty_and_opted_in(self):
        text = (ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual(changelog.FORMAT, changelog.format_of(text))  # new projects start opted in
        self.assertNotIn("## [Unreleased]", onboard._strip_comments(text))
        self.assertEqual([], changelog.lint(text))


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

    def test_kept_lines_do_not_count(self):
        text = doc("- #1: x [user] MAJOR", "- #2: y [app] PATCH", "- #3: z [app]")
        keep = [line_of(text, "#1:"), line_of(text, "#3:")]
        self.assertEqual("1.0.1", changelog.propose(text, "1.0.0", keep))
        with self.assertRaises(changelog.ChangelogError):
            changelog.propose(text, "1.0.0", keep + [line_of(text, "#2:")])
        with self.assertRaises(changelog.ChangelogError):
            changelog.propose(text, "1.0.0", [line_of(text, "#1:")])  # #3 is selected and unmarked

    def test_bad_current_version_refuses(self):
        with self.assertRaises(changelog.ChangelogError):
            changelog.propose(doc("- #1: x [user] MINOR"), "v1.0")


RELEASED = "\n## [1.0.0] — 2026-01-02\n\n### Changes\n- #9: old [user] MAJOR\n"


def line_of(text, needle):
    return next(n for n, ln in enumerate(text.splitlines(), 1) if needle in ln)


class CutTest(unittest.TestCase):
    TEXT = doc("### Added / Changed / Fixed", "- #1: a [meta]", "- #2: b (PR #3) [user] MINOR flags: f1",
               "- #4: c [app] PATCH", "- #5: d [user] MAJOR", released=RELEASED)

    def cut(self, text=None, version="1.1.0", keep=(), notes="- Better things.\n", date="2026-10-23"):
        return changelog.cut(text or self.TEXT, version, list(keep), notes, date)

    def test_everything_moves_and_an_emptied_unreleased_is_removed(self):
        text = doc("- #1: a [user] PATCH", released=RELEASED)
        out = self.cut(text=text, version="2.0.0")
        self.assertTrue(out.startswith(INTRO + "## [2.0.0] — 2026-10-23\n"), out)
        self.assertNotIn("## [Unreleased]", out.replace(FOOTER, ""))

    def test_non_entry_lines_stay_in_unreleased(self):
        text = doc("<!-- keep this note\n- #0: commented out [user] PATCH -->", "### Added / Changed / Fixed",
                   "- #1: a [user] PATCH", released=RELEASED)
        out = self.cut(text=text, version="2.0.0")
        self.assertTrue(out.startswith(INTRO + "## [Unreleased]\n<!-- keep this note\n- #0: commented out [user] PATCH -->\n"
                                       "### Added / Changed / Fixed\n\n## [2.0.0] — 2026-10-23\n"), out)
        self.assertIn("### Changes\n- #1: a [user] PATCH\n\n## [1.0.0]", out)
        self.assertEqual([], changelog.lint(out))

    def test_everything_moves(self):
        out = self.cut(version="2.0.0")
        self.assertTrue(out.startswith(INTRO + "## [Unreleased]\n### Added / Changed / Fixed\n\n## [2.0.0]"), out)
        self.assertIn("## [2.0.0] — 2026-10-23\n\n### Release notes\n- Better things.\n\n### Changes\n"
                      "- #1: a [meta]\n- #2: b (PR #3) [user] MINOR flags: f1\n- #4: c [app] PATCH\n"
                      "- #5: d [user] MAJOR\n\n## [1.0.0] — 2026-01-02", out)
        self.assertTrue(out.endswith(FOOTER))
        self.assertEqual([], changelog.lint(out))

    def test_kept_lines_stay_in_unreleased_and_non_app_lines_move(self):
        keep = [line_of(self.TEXT, "#2:"), line_of(self.TEXT, "#5:")]
        out = self.cut(keep=keep)
        self.assertTrue(out.startswith(INTRO + "## [Unreleased]\n### Added / Changed / Fixed\n"
                                       "- #2: b (PR #3) [user] MINOR flags: f1\n- #5: d [user] MAJOR\n\n"
                                       "## [1.1.0] — 2026-10-23\n"), out)
        self.assertIn("### Changes\n- #1: a [meta]\n- #4: c [app] PATCH\n\n## [1.0.0]", out)
        self.assertEqual([], changelog.lint(out))
        self.assertEqual(["- #2: b (PR #3) [user] MINOR flags: f1", "- #5: d [user] MAJOR"],
                         [e["text"] for e in changelog.unreleased(out)["app"]])

    def test_no_notes_means_no_release_notes_section(self):
        out = self.cut(version="2.0.0", notes="\n  \n")
        self.assertIn("## [2.0.0] — 2026-10-23\n\n### Changes\n", out)
        self.assertNotIn("### Release notes", out)

    def test_first_release_and_unreleased_before_the_rule(self):
        text = INTRO + "## [Unreleased]\n- #1: a [user] PATCH\n\n---\n"
        out = changelog.cut(text, "0.0.1", [], "", "2026-10-23")
        self.assertEqual(INTRO + "## [0.0.1] — 2026-10-23\n\n### Changes\n- #1: a [user] PATCH\n\n---\n", out)

    def test_refusals(self):
        for kwargs, needle in [
            ({"version": "1.0.0"}, "1.0.0"),
            ({"version": "0.9.0"}, "greater"),
            ({"version": "v1.1.0"}, "X.Y.Z"),
            ({"date": "23.10.2026"}, "YYYY-MM-DD"),
            ({"keep": [line_of(self.TEXT, "#1:")]}, "not an app-changing"),
            ({"keep": [999]}, "not an app-changing"),
            ({"keep": [line_of(self.TEXT, n) for n in ("#2:", "#4:", "#5:")]}, "nothing to release"),
            ({"text": doc("- #1: a [meta]")}, "nothing to release"),
            ({"text": doc("- #1: a [user]")}, "mark"),
            ({"text": doc("- #1: a [bogus]")}, "lint"),
            ({"text": doc("- #1: a [user] PATCH").replace("yab-1", "yab-9")}, "yab-9"),
        ]:
            with self.subTest(kwargs), self.assertRaises(changelog.ChangelogError) as cm:
                self.cut(**kwargs)
            self.assertIn(needle, str(cm.exception), kwargs)

    def test_heading_with_trailing_whitespace(self):
        text = INTRO + "## [Unreleased] \t\n- #1: a [user] PATCH\n"
        out = changelog.cut(text, "0.0.1", [], "", "2026-10-23")
        self.assertEqual(INTRO + "## [0.0.1] — 2026-10-23\n\n### Changes\n- #1: a [user] PATCH\n", out)

    def test_crlf_line_endings_are_kept(self):
        text = self.TEXT.replace("\n", "\r\n")
        out = changelog.cut(text, "2.0.0", [line_of(text, "#5:")], "- A.\n", "2026-10-23")
        self.assertNotIn("\n", out.replace("\r\n", ""))
        self.assertEqual(self.cut(version="2.0.0", keep=[line_of(self.TEXT, "#5:")], notes="- A.\n"),
                         out.replace("\r\n", "\n"))

    def test_missing_mark_on_a_kept_line_is_fine(self):
        text = doc("- #1: a [user] PATCH", "- #2: b [app]")
        out = changelog.cut(text, "0.0.1", [line_of(text, "#2:")], "", "2026-10-23")
        self.assertIn("## [Unreleased]\n- #2: b [app]\n", out)

    def test_latest_ignores_pre_releases_and_reads_short_versions(self):
        self.assertEqual("1.0.0", changelog.latest(self.TEXT))
        self.assertIsNone(changelog.latest(doc("- #1: a [meta]")))
        self.assertEqual("1.2.0", changelog.latest(INTRO + "## [2.0.0-rc.1] — 2026-01-03\n## [1.2] — 2026-01-02\n"))
        with self.assertRaises(changelog.ChangelogError):
            changelog.cut(INTRO + "## [Unreleased]\n- #1: a [user] PATCH\n\n## [1.2] — 2026-01-02\n", "1.2.0",
                          [], "", "2026-10-23")


class MarkTest(unittest.TestCase):
    TEXT = doc("- #1: a [meta]", "- #2: b [user]", "- #3: c [app] PATCH")

    def test_supplied_mark_counts_in_propose(self):
        n = line_of(self.TEXT, "#2:")
        self.assertEqual("1.1.0", changelog.propose(self.TEXT, "1.0.0", marks={n: "MINOR"}))
        self.assertEqual("1.0.1", changelog.propose(self.TEXT, "1.0.0", [n], {n: "MINOR"}))

    def test_supplied_mark_is_written_by_cut(self):
        n = line_of(self.TEXT, "#2:")
        out = changelog.cut(self.TEXT, "1.1.0", [], "", "2026-10-23", {n: "MINOR"})
        self.assertIn("- #2: b [user] MINOR\n", out)
        kept = changelog.cut(self.TEXT, "1.0.1", [n], "", "2026-10-23", {n: "MAJOR"})
        self.assertIn("## [Unreleased]\n- #2: b [user] MAJOR\n", kept)
        self.assertEqual([], changelog.lint(kept))

    def test_mark_goes_before_a_trailing_comment(self):
        text = doc("- A-3: x [app] <!-- c -->", "- A-4: y [user]  <!-- d --> <!-- e -->", "- A-5: z [app] <!-- open")
        text = text.replace("<!-- open\n", "<!-- open\nstill comment -->\n")
        marks = {line_of(text, "A-3"): "MINOR", line_of(text, "A-4"): "PATCH", line_of(text, "A-5"): "MAJOR"}
        out = changelog.apply_marks(text, marks)
        self.assertIn("- A-3: x [app] MINOR <!-- c -->\n", out)
        self.assertIn("- A-4: y [user] PATCH  <!-- d --> <!-- e -->\n", out)
        self.assertIn("- A-5: z [app] MAJOR <!-- open\n", out)
        self.assertEqual([], changelog.lint(out))
        self.assertEqual("2.0.0", changelog.propose(text, "1.0.0", marks=marks))

    def test_refusals(self):
        for marks, needle in [
            ({line_of(MarkTest.TEXT, "#1:"): "PATCH"}, "not an app-changing"),
            ({line_of(MarkTest.TEXT, "#3:"): "MINOR"}, "already"),
            ({line_of(MarkTest.TEXT, "#2:"): "minor"}, "MAJOR, MINOR or PATCH"),
        ]:
            with self.subTest(marks), self.assertRaises(changelog.ChangelogError) as cm:
                changelog.propose(self.TEXT, "1.0.0", marks=marks)
            self.assertIn(needle, str(cm.exception))


class NotesTest(unittest.TestCase):
    def test_round_trip(self):
        out = changelog.cut(CutTest.TEXT, "2.0.0", [], "\n- One.\n- Two.\n\n", "2026-10-23")
        self.assertEqual("- One.\n- Two.", changelog.notes(out, "2.0.0"))
        self.assertEqual("", changelog.notes(out, "1.0.0"))

    def test_unknown_version_refuses(self):
        with self.assertRaises(changelog.ChangelogError):
            changelog.notes(CutTest.TEXT, "3.0.0")

    def test_section_ends_at_next_subheading_and_comments_are_skipped(self):
        text = INTRO + "## [1.0.0] — 2026-01-02\n### Release notes\n- A.\n<!-- hidden -->\n### Changes\n- #1: x [user] PATCH\n"
        self.assertEqual("- A.", changelog.notes(text, "1.0.0"))


class CodeRepoPrReferenceTest(unittest.TestCase):
    """Two-repo sessions cite the code repo's PR as (PR owner/repo#N); every command treats it like (PR #N)."""
    LINES = ("- YD-3: a (PR o/code-repo#7) [meta]", "- YD-4: b (PR o/code.repo#8) [user] MINOR flags: f1",
             "- YD-5: c (PR #9) [app] PATCH")
    TEXT = doc(*LINES, released=RELEASED)

    def test_lint_accepts_it(self):
        self.assertEqual([], errors(self.TEXT))

    def test_unreleased_reports_it(self):
        result = changelog.unreleased(self.TEXT)
        self.assertEqual(list(self.LINES[1:]), [e["text"] for e in result["app"]])
        self.assertEqual(1, result["non_app"])

    def test_cut_moves_it_and_notes_leave_it_out(self):
        out = changelog.cut(self.TEXT, "1.1.0", [], "- Better things.\n", "2026-10-23")
        self.assertIn("### Changes\n%s\n\n## [1.0.0]" % "\n".join(self.LINES), out)
        self.assertEqual([], changelog.lint(out))
        self.assertEqual("- Better things.", changelog.notes(out, "1.1.0"))


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

    def test_cut_writes_the_file(self):
        path = self.write(CutTest.TEXT)
        notes = self.write("- Better things.\n")
        code, out = self.run_main("cut", path, "1.1.0", "--keep", str(line_of(CutTest.TEXT, "#5:")),
                                  "--notes-file", notes, "--date", "2026-10-23")
        self.assertEqual(0, code, out)
        self.assertEqual({"version": "1.1.0", "moved": 3, "kept": 1}, out)
        text = Path(path).read_text(encoding="utf-8")
        self.assertIn("## [1.1.0] — 2026-10-23", text)
        self.assertEqual("- Better things.", changelog.notes(text, "1.1.0"))

    def test_cut_keeps_crlf_on_disk(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        path = Path(d.name) / "CHANGELOG.md"
        path.write_bytes(CutTest.TEXT.replace("\n", "\r\n").encode("utf-8"))
        code, out = self.run_main("cut", str(path), "2.0.0", "--date", "2026-10-23")
        self.assertEqual(0, code, out)
        data = path.read_bytes()
        self.assertIn(b"## [2.0.0]", data)
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))

    def test_mark_option(self):
        path = self.write(MarkTest.TEXT)
        n = str(line_of(MarkTest.TEXT, "#2:"))
        self.assertEqual((0, {"version": "2.0.0"}), self.run_main("propose", path, "--current", "1.0.0", "--mark", n + "=MAJOR"))
        code, out = self.run_main("propose", path, "--current", "1.0.0", "--mark", n + ":MAJOR")
        self.assertEqual(1, code)
        self.assertIn("LINE=MARK", out["error"])
        code, out = self.run_main("cut", path, "1.1.0", "--mark", n + "=MINOR", "--date", "2026-10-23")
        self.assertEqual(0, code, out)
        self.assertIn("- #2: b [user] MINOR", Path(path).read_text(encoding="utf-8"))

    def test_cut_refusal_leaves_the_file(self):
        path = self.write(CutTest.TEXT)
        code, out = self.run_main("cut", path, "1.0.0")
        self.assertEqual(1, code)
        self.assertIn("error", out)
        self.assertEqual(CutTest.TEXT, Path(path).read_text(encoding="utf-8"))

    def test_latest(self):
        self.assertEqual((0, {"version": "1.0.0"}), self.run_main("latest", self.write(CutTest.TEXT)))
        self.assertEqual((0, {"version": None}), self.run_main("latest", self.write(doc("- #1: a [meta]"))))

    def test_notes_prints_plain_text(self):
        text = changelog.cut(CutTest.TEXT, "2.0.0", [], "- One.\n", "2026-10-23")
        out = io.StringIO()
        with redirect_stdout(out):
            code = changelog.main(["notes", self.write(text), "2.0.0"])
        self.assertEqual((0, "- One.\n"), (code, out.getvalue()))
        code, out = self.run_main("notes", self.write(text), "9.9.9")
        self.assertEqual(1, code)
        self.assertIn("error", out)

    def test_propose_with_keep(self):
        text = doc("- #1: x [user] MAJOR", "- #2: y [app] PATCH")
        out = self.run_main("propose", self.write(text), "--current", "1.0.0", "--keep", str(line_of(text, "#1:")))
        self.assertEqual((0, {"version": "1.0.1"}), out)

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
