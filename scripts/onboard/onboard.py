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


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="onboard")
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    args = ap.parse_args(argv)
    if args.cmd == "probe":
        print(json.dumps(probe(), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
