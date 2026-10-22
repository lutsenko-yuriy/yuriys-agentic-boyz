#!/usr/bin/env python3
"""Generic CHANGELOG tool: lint the `[Unreleased]` line grammar and propose the next version.

Usage:
    python3 scripts/changelog/changelog.py lint <path>                         # grammar findings
    python3 scripts/changelog/changelog.py unreleased <path>                   # app-changing [Unreleased] lines
    python3 scripts/changelog/changelog.py propose <path> --current X.Y.Z      # next version from the highest mark

Line grammar (skills/manage/ship/resources/changelog-tags.md):
    - <ID>: <summary> (PR #N) [tag]... <MAJOR|MINOR|PATCH> flags: <name>, <name>   (mark and flags as the rules require)

Only `## [Unreleased]` lines are linted; numbered `## [X.Y.Z]` sections are checked for their heading format only.
Prints JSON on stdout. Exit codes: 0 ok, 1 findings or refusal.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CLASSIFICATION_TAGS = ("user", "app", "test", "meta", "ci", "wip")
TAGS = CLASSIFICATION_TAGS + ("non-user",)
APP_TAGS = ("user", "app")
MARKS = ("PATCH", "MINOR", "MAJOR")  # ascending precedence
SUBCOMMANDS = ("lint", "unreleased", "propose")

UNRELEASED = "## [Unreleased]"
NUMBERED_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\] — \d{4}-\d{2}-\d{2}(?: \(.*\))?$")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
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
    return _scan(text)[0]


def unreleased(text: str) -> Dict[str, Any]:
    """App-changing [Unreleased] lines and a count of the rest. A missing mark is reported as None, not refused."""
    findings, entries = _scan(text)
    parsed = {n for n, _, _ in entries}
    if any(f["line"] not in parsed for f in findings):
        raise ChangelogError("CHANGELOG has lint findings", findings)
    app = [{"line": n, "text": line, **e} for n, line, e in entries if any(t in APP_TAGS for t in e["tags"])]
    return {"app": app, "non_app": len(entries) - len(app)}


def propose(text: str, current: str) -> str:
    m = VERSION_RE.match(current)
    if not m:
        raise ChangelogError("current version %r is not X.Y.Z" % current)
    app = unreleased(text)["app"]
    if not app:
        raise ChangelogError("no [user]/[app] lines in [Unreleased]: nothing to release")
    missing = [e["line"] for e in app if e["mark"] is None]
    if missing:
        raise ChangelogError("missing semver mark on line(s) %s" % ", ".join(map(str, missing)))
    top = max(MARKS.index(e["mark"]) for e in app)
    major, minor, patch = (int(g) for g in m.groups())
    return ["%d.%d.%d" % (major, minor, patch + 1), "%d.%d.0" % (major, minor + 1), "%d.0.0" % (major + 1)][top]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in SUBCOMMANDS:
        p = sub.add_parser(name)
        p.add_argument("path")
        if name == "propose":
            p.add_argument("--current", required=True)
    args = parser.parse_args(argv)
    try:
        text = Path(args.path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(json.dumps({"error": str(e)}))
        return 1
    if args.cmd == "lint":
        findings = lint(text)
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 1 if findings else 0
    try:
        if args.cmd == "unreleased":
            result = unreleased(text)
        else:
            result = {"version": propose(text, args.current)}
    except ChangelogError as e:
        print(json.dumps({"error": str(e), "findings": e.findings} if e.findings else {"error": str(e)}, indent=2))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
