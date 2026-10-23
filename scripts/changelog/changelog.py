#!/usr/bin/env python3
"""Generic CHANGELOG tool: lint the `[Unreleased]` line grammar, propose the next version and cut a release.

Usage:
    python3 scripts/changelog/changelog.py lint <path>                         # grammar findings
    python3 scripts/changelog/changelog.py unreleased <path>                   # app-changing [Unreleased] lines
    python3 scripts/changelog/changelog.py propose <path> --current X.Y.Z [--keep N ...] [--mark N=MARK ...]
        # next version from the highest mark among the lines not kept; --mark supplies a missing mark
    python3 scripts/changelog/changelog.py latest <path>                       # latest released X.Y.Z, or null
    python3 scripts/changelog/changelog.py cut <path> X.Y.Z [--keep N ...] [--mark N=MARK ...] [--notes-file F] [--date D]
        # release commit content: every [Unreleased] line except the kept app lines (file line numbers, as
        # `unreleased` reports them) moves under a new `## [X.Y.Z] — date` heading with `### Release notes`
        # (from F, omitted when empty) and `### Changes`; comments and subheadings stay, and an `## [Unreleased]` left empty is removed
    python3 scripts/changelog/changelog.py notes <path> X.Y.Z                  # that release's notes, plain text

Line grammar (skills/manage/ship/resources/changelog-tags.md):
    - <ID>: <summary> (PR #N) [tag]... <MAJOR|MINOR|PATCH> flags: <name>, <name>   (mark and flags as the rules require)

Only a CHANGELOG with the format marker line `<!-- changelog-format: yab-1 -->` above the first `---` is linted (a second
marker anywhere is a finding); without it `lint` prints a notice and exits 0, and `unreleased`/`propose` still parse
but add the notice to their output; an unknown format is refused by all three.
Only `## [Unreleased]` lines are linted; numbered `## [X.Y.Z]` sections are checked for their heading format only.
Prints JSON on stdout (`notes` prints its plain text on success). Exit codes: 0 ok, 1 findings or refusal.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

CLASSIFICATION_TAGS = ("user", "app", "test", "meta", "ci", "wip")
TAGS = CLASSIFICATION_TAGS + ("non-user",)
APP_TAGS = ("user", "app")
MARKS = ("PATCH", "MINOR", "MAJOR")  # ascending precedence
SUBCOMMANDS = ("lint", "unreleased", "propose", "latest", "cut", "notes")

FORMAT = "yab-1"
MARKER = "<!-- changelog-format: %s -->" % FORMAT
MARKER_RE = re.compile(r"^<!-- changelog-format: (\S+) -->$")
NOTICE = "no %s line: not linted; add it above the first '---' to opt in (docs/VERSIONING.md)" % MARKER

UNRELEASED = "## [Unreleased]"
UNRELEASED_LIKE_RE = re.compile(r"^##\s+\[?\s*unreleased\b", re.IGNORECASE)
# Grandfathered: X.Y or X.Y.Z with optional pre-release/build, `-`/`–`/`—`, `??` date parts, or no date;
# Keep a Changelog's trailing ` [YANKED]` is allowed.
NUMBERED_RE = re.compile(r"^## \[\d+\.\d+(?:\.\d+)?(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\]"
                         r"(?: [-–—] \d{4}-(?:\d{2}|\?\?)-(?:\d{2}|\?\?)(?: \(.*\))?)?(?: \[YANKED\])?$")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# A numbered heading's version: X.Y or X.Y.Z, then the pre-release/build suffix (if any) and the rest.
HEADING_VERSION_RE = re.compile(r"^## \[(\d+)\.(\d+)(?:\.(\d+))?([-+][^\]]*)?\]")
RELEASE_NOTES = "### Release notes"
CHANGES = "### Changes"
ENTRY_RE = re.compile(r"^- (?P<id>[^\s:][^:]*): (?P<rest>.+)$")
TAIL_RE = re.compile(r"^(?P<summary>.*?)(?P<tags>(?: \[[^\[\]\s]+\])+)(?: (?P<mark>[A-Za-z]+))?(?: flags:(?P<flags>.*))?$")
FLAG_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


class ChangelogError(Exception):
    def __init__(self, message: str, findings: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.findings = findings


def _blank_comments(text: str) -> List[str]:
    """Lines with HTML comments blanked, so line numbers still match the file."""
    return COMMENT_RE.sub(lambda m: re.sub(r"[^\n]", "", m.group(0)), text).splitlines()


def _markers(text: str) -> List[Tuple[int, str, bool]]:
    """[(line number, format, in intro)] for each marker line; the intro ends at the first '---' line.

    A BOM, CRLF and surrounding whitespace are ignored.
    """
    found, intro = [], True
    for n, raw in enumerate(text.lstrip("\ufeff").splitlines(), 1):
        line = raw.strip()
        if line == "---":
            intro = False
        m = MARKER_RE.match(line)
        if m:
            found.append((n, m.group(1), intro))
    return found


def _unknown_format(fmt: str) -> str:
    return "unknown changelog format %r; supported: %s" % (fmt, FORMAT)


def format_of(text: str) -> Optional[str]:
    """The format named by the first marker line in the intro, or None for a CHANGELOG that has not opted in."""
    opt_in = [fmt for _, fmt, intro in _markers(text) if intro]
    return opt_in[0] if opt_in else None


def parse_entry(line: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """(entry, None) for a valid line, else the first error; a missing mark still returns the entry."""
    m = ENTRY_RE.match(line)
    if not m:
        return None, "expected '- <ID>: <summary> … [tag]'"
    tail = TAIL_RE.match(" " + m.group("rest"))
    if not tail or not tail.group("summary").strip():
        return None, "no classification tag at the end of the line"
    tags = re.findall(r"\[([^\]]+)\]", tail.group("tags"))
    for tag in tags:
        if tag not in TAGS:
            return None, "unknown tag [%s]; known: %s" % (tag, ", ".join(TAGS))
        if tags.count(tag) > 1:
            return None, "tag [%s] appears twice" % tag
    if not any(t in CLASSIFICATION_TAGS for t in tags):
        return None, "[non-user] needs a classification tag: %s" % ", ".join(CLASSIFICATION_TAGS)
    mark, raw_flags = tail.group("mark"), tail.group("flags")
    app = any(t in APP_TAGS for t in tags)
    if mark is not None and mark not in MARKS:
        return None, "unknown mark %r; use %s" % (mark, ", ".join(reversed(MARKS)))
    if app and mark is None:
        return {"tags": tags, "mark": None, "flags": []}, "[user]/[app] lines need a semver mark: MAJOR, MINOR or PATCH"
    if not app and mark is not None:
        return None, "mark %s is only allowed on [user]/[app] lines" % mark
    flags: List[str] = []
    if raw_flags is not None:
        if mark is None:
            return None, "flags: is only allowed after a mark"
        flags = [f.strip() for f in raw_flags.split(",")]
        bad = [f for f in flags if not FLAG_RE.match(f)]
        if bad:
            return None, "bad flag name %r (allowed: letters, digits, _ . -)" % bad[0]
    return {"tags": tags, "mark": mark, "flags": flags}, None


def _scan(text: str) -> Tuple[List[Dict[str, Any]], List[Tuple[int, str, Dict[str, Any]]]]:
    """(findings, [(line number, text, entry)] for every parsed [Unreleased] line)."""
    findings: List[Dict[str, Any]] = []
    entries: List[Tuple[int, str, Dict[str, Any]]] = []
    section, seen_unreleased, seen_numbered = None, False, False
    for n, raw in enumerate(_blank_comments(text), 1):
        line = raw.rstrip()
        if line.startswith("## "):
            section = None
            if line == UNRELEASED:
                if seen_unreleased or seen_numbered:
                    findings.append({"line": n, "error": "only one ## [Unreleased], above every release"})
                seen_unreleased, section = True, "unreleased"
            elif UNRELEASED_LIKE_RE.match(line):
                findings.append({"line": n, "error": "Unreleased heading must be exactly '%s'" % UNRELEASED})
            elif line.startswith("## ["):
                seen_numbered = True
                if not NUMBERED_RE.match(line):
                    findings.append({"line": n, "error": "bad release heading; expected '## [X.Y.Z] — YYYY-MM-DD'"})
            continue
        if section != "unreleased" or not line or line.startswith("### ") or line == "---":
            continue
        if not line.startswith("- "):
            findings.append({"line": n, "error": "unexpected line in [Unreleased]; expected '- <ID>: …'"})
            continue
        entry, error = parse_entry(line)
        if error:
            findings.append({"line": n, "error": error})
        if entry is not None:
            entries.append((n, line, entry))
    return findings, entries


def lint(text: str) -> List[Dict[str, Any]]:
    """Findings for a CHANGELOG with the format marker; none for one without it."""
    markers = _markers(text)
    opt_in = [m for m in markers if m[2]]
    if not opt_in:
        return []
    line, fmt, _ = opt_in[0]
    findings = [{"line": n, "error": "second changelog-format marker; keep only the one above the first '---'"}
                for n, _, _ in markers if n != line]
    if fmt != FORMAT:
        return [{"line": line, "error": _unknown_format(fmt)}] + findings
    return sorted(findings + _scan(text)[0], key=lambda f: f["line"])


def unreleased(text: str) -> Dict[str, Any]:
    """App-changing [Unreleased] lines and a count of the rest. A missing mark is reported as None, not refused."""
    fmt = format_of(text)
    if fmt not in (None, FORMAT):
        raise ChangelogError(_unknown_format(fmt))
    findings, entries = _scan(text)
    parsed = {n for n, _, _ in entries}
    if any(f["line"] not in parsed for f in findings):
        raise ChangelogError("CHANGELOG has lint findings", findings)
    app = [{"line": n, "text": line, **e} for n, line, e in entries if any(t in APP_TAGS for t in e["tags"])]
    return {"app": app, "non_app": len(entries) - len(app)}


def _selected(app: List[Dict[str, Any]], keep: Sequence[int]) -> List[Dict[str, Any]]:
    """The app lines not kept back; refuses stray keep numbers, an empty selection and unmarked selected lines."""
    stray = sorted(set(keep) - {e["line"] for e in app})
    if stray:
        raise ChangelogError("line(s) %s not an app-changing [Unreleased] line" % ", ".join(map(str, stray)))
    selected = [e for e in app if e["line"] not in keep]
    if not selected:
        raise ChangelogError("no [user]/[app] lines selected in [Unreleased]: nothing to release")
    missing = [e["line"] for e in selected if e["mark"] is None]
    if missing:
        raise ChangelogError("missing semver mark on selected line(s) %s" % ", ".join(map(str, missing)))
    return selected


def apply_marks(text: str, marks: Dict[int, str]) -> str:
    """text with each mark appended to its unmarked app line (file line number -> MARK); lines do not move."""
    if not marks:
        return text
    app = {e["line"]: e for e in unreleased(text)["app"]}
    lines = text.splitlines(True)
    for n, mark in sorted(marks.items()):
        if mark not in MARKS:
            raise ChangelogError("mark %r for line %d: use MAJOR, MINOR or PATCH" % (mark, n))
        if n not in app:
            raise ChangelogError("line %d is not an app-changing [Unreleased] line" % n)
        if app[n]["mark"] is not None:
            raise ChangelogError("line %d already has mark %s" % (n, app[n]["mark"]))
        body = lines[n - 1].rstrip("\r\n")
        lines[n - 1] = body.rstrip() + " " + mark + lines[n - 1][len(body):]
    return "".join(lines)


def _parse_marks(raw: Sequence[str]) -> Dict[int, str]:
    marks: Dict[int, str] = {}
    for item in raw:
        m = re.match(r"^(\d+)=(\S+)$", item)
        if not m:
            raise ChangelogError("--mark takes LINE=MARK, not %r" % item)
        marks[int(m.group(1))] = m.group(2)
    return marks


def propose(text: str, current: str, keep: Sequence[int] = (), marks: Optional[Dict[int, str]] = None) -> str:
    """The next version from the highest mark among the app lines not kept back; marks fill unmarked lines."""
    m = VERSION_RE.match(current)
    if not m:
        raise ChangelogError("current version %r is not X.Y.Z" % current)
    text = apply_marks(text, marks or {})
    selected = _selected(unreleased(text)["app"], keep)
    top = max(MARKS.index(e["mark"]) for e in selected)
    major, minor, patch = (int(g) for g in m.groups())
    return ["%d.%d.%d" % (major, minor, patch + 1), "%d.%d.0" % (major, minor + 1), "%d.0.0" % (major + 1)][top]


def _versions(text: str) -> List[Tuple[str, Optional[Tuple[int, int, int]]]]:
    """(version as written, (X, Y, Z) or None for a pre-release/build) for each numbered heading."""
    out = []
    for line in _blank_comments(text):
        m = HEADING_VERSION_RE.match(line.rstrip())
        if m:
            core = (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))
            written = line[len("## ["):line.index("]")]
            out.append((written, None if m.group(4) else core))
    return out


def latest(text: str) -> Optional[str]:
    """The highest released X.Y.Z (X.Y counts as X.Y.0; pre-releases are skipped), or None."""
    cores = [core for _, core in _versions(text) if core]
    return "%d.%d.%d" % max(cores) if cores else None


def _section_end(lines: List[str], start: int) -> int:
    """Index of the next `## ` heading or `---` rule after the heading at start (lines are comment-blanked)."""
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## ") or lines[i].strip() == "---":
            return i
    return len(lines)


def cut(text: str, version: str, keep: List[int], notes_text: str, date: str,
        marks: Optional[Dict[int, str]] = None) -> str:
    """The CHANGELOG after releasing version; keep holds file line numbers of app lines that stay in [Unreleased],
    marks the marks the user supplied for unmarked app lines (written to those lines)."""
    m = VERSION_RE.match(version)
    if not m:
        raise ChangelogError("version %r is not X.Y.Z" % version)
    if not DATE_RE.match(date):
        raise ChangelogError("date %r is not YYYY-MM-DD" % date)
    if any(written == version for written, _ in _versions(text)):
        raise ChangelogError("## [%s] already exists" % version)
    previous = latest(text)
    if previous and tuple(int(g) for g in m.groups()) <= tuple(int(g) for g in previous.split(".")):
        raise ChangelogError("version %s must be greater than the latest release %s" % (version, previous))
    try:
        text = apply_marks(text, marks or {})
        app = unreleased(text)["app"]
    except ChangelogError as e:
        if e.findings:
            raise ChangelogError("CHANGELOG has lint findings; fix them first", e.findings)
        raise
    _selected(app, keep)

    raw = text.splitlines()
    blanked = _blank_comments(text)
    start = next(i for i, ln in enumerate(blanked) if ln.rstrip() == UNRELEASED)  # as _scan matches it
    end = _section_end(blanked, start)
    entries = {n - 1 for n, _, _ in _scan(text)[1]}
    moved = [raw[i] for i in range(start + 1, end) if i in entries and i + 1 not in keep]
    body = [raw[i] for i in range(start + 1, end) if not (i in entries and i + 1 not in keep)]
    while body and not body[-1].strip():
        body.pop()
    # Comments, subheadings and kept lines stay; an [Unreleased] left with only blank lines is removed.
    head = [raw[start]] + body + [""] if any(ln.strip() for ln in body) else []
    notes_lines = notes_text.strip("\n").splitlines() if notes_text.strip() else []
    release = ["## [%s] — %s" % (version, date), ""]
    if notes_lines:
        release += [RELEASE_NOTES] + notes_lines + [""]
    release += [CHANGES] + moved + ([""] if raw[end:] else [])
    out = raw[:start] + head + release + raw[end:]
    eol = "\r\n" if "\r\n" in text else "\n"  # a CRLF file stays CRLF
    return eol.join(out) + eol


def notes(text: str, version: str) -> str:
    """The `### Release notes` body of version's section ("" when it has none), for release jobs."""
    raw, blanked = text.splitlines(), _blank_comments(text)
    starts = [i for i, ln in enumerate(blanked) if ln.startswith("## [%s]" % version)]
    if not starts:
        raise ChangelogError("no ## [%s] heading" % version)
    end = _section_end(blanked, starts[0])
    out: List[str] = []
    inside = False
    for i in range(starts[0] + 1, end):
        if blanked[i].startswith("### "):
            inside = blanked[i].rstrip() == RELEASE_NOTES
        elif inside and blanked[i].strip():
            out.append(raw[i])
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in SUBCOMMANDS:
        p = sub.add_parser(name)
        p.add_argument("path")
        if name == "propose":
            p.add_argument("--current", required=True)
        if name in ("cut", "notes"):
            p.add_argument("version")
        if name in ("propose", "cut"):
            p.add_argument("--keep", type=int, nargs="*", default=[])
            p.add_argument("--mark", nargs="*", default=[], help="LINE=MARK for an unmarked app line")
        if name == "cut":
            p.add_argument("--notes-file")
            p.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args(argv)
    try:
        with open(args.path, encoding="utf-8", newline="") as f:  # newline="": keep CRLF for cut
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(json.dumps({"error": str(e)}))
        return 1
    notice = {} if format_of(text) else {"notice": NOTICE}
    if args.cmd == "lint":
        if notice:
            print(json.dumps(dict(findings=[], **notice), ensure_ascii=False))
            return 0
        findings = lint(text)
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 1 if findings else 0
    try:
        if args.cmd == "unreleased":
            result = unreleased(text)
        elif args.cmd == "propose":
            result = {"version": propose(text, args.current, args.keep, _parse_marks(args.mark))}
        elif args.cmd == "latest":
            result = {"version": latest(text)}
        elif args.cmd == "notes":
            body = notes(text, args.version)
            if body:
                print(body)
            return 0
        else:
            try:
                notes_text = Path(args.notes_file).read_text(encoding="utf-8") if args.notes_file else ""
            except (OSError, UnicodeDecodeError) as e:
                raise ChangelogError(str(e))
            new = cut(text, args.version, args.keep, notes_text, args.date, _parse_marks(args.mark))
            with open(args.path, "w", encoding="utf-8", newline="") as f:
                f.write(new)
            result = {"version": args.version, "moved": len(_scan(text)[1]) - len(set(args.keep)),
                      "kept": len(set(args.keep))}
    except ChangelogError as e:
        error = {"error": str(e), "findings": e.findings} if e.findings else {"error": str(e)}
        print(json.dumps(dict(error, **notice), indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(dict(result, **notice), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
