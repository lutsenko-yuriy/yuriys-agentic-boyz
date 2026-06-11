import re
import shutil
import subprocess


def _find_gh() -> str:
    return shutil.which("gh") or "/opt/homebrew/bin/gh"


def _get_github_repo() -> str:
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", r.stdout.strip())
        return m.group(1) if m else ""
    except Exception:
        return ""
