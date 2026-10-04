#!/usr/bin/env python3
"""Deterministic onboarding helper: probe the machine, check the repo, mark it onboarded.

Usage:
    python3 scripts/onboard/onboard.py probe            # read-only machine report (Python 3.9 ok)
    python3 scripts/onboard/onboard.py check            # read-only JSON report; exit 1 if not clean
    python3 scripts/onboard/onboard.py mark [--force]   # write the per-clone onboarded marker

`check` and `mark` read skill_router.toml and need Python 3.11+ (tomllib); they fail loudly (exit 2) otherwise.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{1,9}$")
PREFIX_REJECT = {"NA"}
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
TEMPLATE_MARKER = "<!-- yab:template -->"
ARTIFACTS = ["docs/TECH_STACK.md", "docs/CODE_STYLE.md", "docs/CONSTRAINTS.md"]
REQUIRED_PROJECT_FIELDS = ["name", "description", "issue_prefix"]
NOTES_DIR = "docs/knowledge/notes"
NOTES_SKIP = {"BOOKMARKS.md", "INDEX.md", "TEMPLATE.md"}
TOOLCHAINS = ["git", "gh", "ollama", "flutter", "dart", "node", "npm", "java", "gradle", "kotlinc", "cargo", "go", "ruby"]
ENV_KEY_RE = re.compile(r"(_API_KEY|_TOKEN)$")


def valid_prefix(prefix: str) -> bool:
    return bool(PREFIX_RE.match(prefix)) and prefix.upper() not in PREFIX_REJECT


def default_prefix(name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", name)
    if len(words) > 1:
        return "".join(w[0] for w in words).upper()
    word = words[0] if words else ""
    humps = re.findall(r"[A-Z]", word)
    if len(humps) > 1 and not word.isupper():
        return "".join(humps)
    return word[:3].upper()


def load_toml(path: Path) -> Dict[str, Any]:
    try:
        import tomllib
    except ImportError:
        sys.stderr.write("onboard: tomllib unavailable (Python < 3.11); use python3.11+, e.g. python3.12\n")
        raise SystemExit(2)
    with open(path, "rb") as f:
        return tomllib.load(f)


def _run(cmd: List[str], cwd: Optional[Path] = None) -> str:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=10).stdout.strip()


def probe(run_tools: bool = True) -> Dict[str, Any]:
    """Names only, never env values; toolchains detected via which, never executed."""
    data = {
        "env_vars_set": sorted(k for k, v in os.environ.items() if v and ENV_KEY_RE.search(k)),
        "toolchains": {t: shutil.which(t) is not None for t in TOOLCHAINS},
        "pythons_with_tomllib": [
            n for n in ("python3.11", "python3.12", "python3.13", "python3.14") if shutil.which(n)
        ],
    }
    if run_tools:
        try:
            if data["toolchains"]["ollama"]:
                lines = _run(["ollama", "list"]).splitlines()[1:]
                data["ollama_models"] = [ln.split()[0] for ln in lines if ln.strip()]
            if data["toolchains"]["gh"]:
                data["gh_authenticated"] = subprocess.run(
                    ["gh", "auth", "status"], capture_output=True, timeout=10
                ).returncode == 0
        except (OSError, subprocess.SubprocessError):
            pass
    return data


def _git(root: Path, *args: str) -> str:
    return _run(["git", "-C", str(root), *args])


def _tracked_files(root: Path) -> List[str]:
    out = subprocess.run(
        ["git", "-C", str(root), "-c", "core.quotePath=false", "ls-files", "-z"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [f for f in out.split("\0") if f]


def _section(text: str, heading: str) -> str:
    m = re.search(r"^##\s+%s\s*$(.*?)(?=^##\s|\Z)" % re.escape(heading), text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""


def _languages(tech_stack: str) -> List[str]:
    rows = [ln for ln in _section(tech_stack, "Languages").splitlines() if ln.strip().startswith("|")]
    names = [r.strip().strip("|").split("|")[0].strip().strip("`*") for r in rows[2:]]
    return [n for n in names if n]


def _check_config(root: Path, errors: List[str]) -> str:
    path = root / "skill_router.toml"
    if not path.is_file():
        errors.append("skill_router.toml missing")
        return ""
    cfg = load_toml(path)
    project = cfg.get("project", {})
    for field in REQUIRED_PROJECT_FIELDS:
        if not str(project.get(field, "")).strip():
            errors.append("project.%s is empty" % field)
    prefix = str(project.get("issue_prefix", "")).strip()
    if prefix and not valid_prefix(prefix):
        errors.append("project.issue_prefix %r is invalid (letters/digits, 2-10 chars, not N/A)" % prefix)
    if not str(cfg.get("providers", {}).get("pm", "")).strip():
        errors.append("providers.pm is empty")
    return prefix


def check(root: Path) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    placeholders: Dict[str, List[str]] = {}
    for rel in _tracked_files(root):
        if rel.startswith("scripts/onboard/"):
            continue
        try:
            found = sorted(set(PLACEHOLDER_RE.findall((root / rel).read_text(encoding="utf-8"))))
        except (UnicodeDecodeError, OSError):
            continue
        if found:
            placeholders[rel] = found
    if placeholders:
        errors.append("%d file(s) still contain {{...}} placeholders" % len(placeholders))
    texts = {}
    for rel in ARTIFACTS:
        p = root / rel
        if not p.is_file():
            errors.append("%s missing" % rel)
        else:
            texts[rel] = p.read_text(encoding="utf-8")
            if TEMPLATE_MARKER in texts[rel]:
                errors.append("%s is still a template" % rel)
    prefix = _check_config(root, errors)
    if "docs/TECH_STACK.md" in texts and "docs/CODE_STYLE.md" in texts:
        base = _section(texts["docs/CODE_STYLE.md"], "Base standard").lower()
        for lang in _languages(texts["docs/TECH_STACK.md"]):
            if lang.lower() not in base:
                errors.append("CODE_STYLE Base standard does not cover TECH_STACK language %s" % lang)
    notes = root / NOTES_DIR
    if prefix and valid_prefix(prefix) and notes.is_dir():
        pat = re.compile(r"^%s-\d+" % re.escape(prefix))
        for n in sorted(notes.glob("*.md")):
            if n.name not in NOTES_SKIP and not pat.match(n.name):
                warnings.append("note %s does not match prefix %s-N" % (n.name, prefix))
    return {
        "ok": not errors,
        "template_mode": (root / ".yab-template").exists(),
        "errors": errors,
        "warnings": warnings,
        "placeholders": placeholders,
    }


def marker_path(root: Path) -> Path:
    common = Path(_git(root, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = root / common
    return common.resolve() / "yab" / "onboarded"


def mark(root: Path, force: bool) -> int:
    if not force and not check(root)["ok"]:
        sys.stderr.write("onboard: check is not clean; refusing to mark (fix issues, or --force)\n")
        return 1
    marker = marker_path(root)
    marker.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    marker.write_text("onboarded=%s\nsha=%s\n" % (stamp, _git(root, "rev-parse", "HEAD")))
    print(marker)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="onboard")
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    sub.add_parser("check")
    sub.add_parser("mark").add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    if args.cmd == "probe":
        print(json.dumps(probe(), indent=2))
        return 0
    if args.cmd == "check":
        result = check(root)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    return mark(root, args.force)


if __name__ == "__main__":
    sys.exit(main())
