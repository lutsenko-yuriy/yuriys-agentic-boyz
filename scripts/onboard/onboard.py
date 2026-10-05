#!/usr/bin/env python3
"""Deterministic onboarding helper: probe the machine, check the repo, mark it onboarded.

Usage:
    python3 scripts/onboard/onboard.py probe            # read-only machine report (Python 3.9 ok)
    python3 scripts/onboard/onboard.py check            # read-only JSON report; exit 1 if not clean
    python3 scripts/onboard/onboard.py apply            # fill placeholders from skill_router.toml, reconcile the rest
    python3 scripts/onboard/onboard.py mark [--force]   # write the per-clone onboarded marker

`check`, `apply` and `mark` read skill_router.toml and need Python 3.11+ (tomllib); they fail loudly (exit 2) otherwise.
Exit codes: 0 ok, 1 check not clean / mark or apply refused, 2 no tomllib, 3 could not run (not a git repo, bad TOML, ...).
"""

import argparse
import datetime
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{1,9}$")
PREFIX_REJECT = {"NA"}
KNOWN_PLACEHOLDERS = [
    "AI_COMMIT_TRAILER", "AI_TOOL_CREDIT", "ARCHITECTURE_SUMMARY", "AVAILABLE_MODELS", "CODE_STYLE",
    "EXPERIMENT_TOOL", "FRAMEWORK", "GIT_HOST", "INTEGRATION_TEST_DIR", "IN_QA_PATHS", "ISSUE_PREFIX",
    "PERSISTENCE", "PM_PROJECT_URL", "PM_TOOL", "PROJECT_DESCRIPTION", "PROJECT_ID", "PROJECT_NAME", "STACK",
    "STATE_MANAGEMENT", "TEAM_ID", "TEST_COMMAND", "TEST_HARNESS_CLASS", "TEST_HARNESS_FILE", "VERSION_FIELD",
    "VERSION_FILE",
]
# Lookarounds keep brace-escapes like f"{{{X}}}" or ${{X}} from matching.
PLACEHOLDER_RE = re.compile(r"(?<![{$])\{\{(?:%s)\}\}(?!\})" % "|".join(KNOWN_PLACEHOLDERS))
# Historical text may quote placeholders legitimately; knowledge-base READMEs/TEMPLATEs are real templates.
SCAN_SKIP_DIRS = ("scripts/onboard/", "docs/knowledge/")
SCAN_SKIP_FILES = {"docs/CHANGELOG.md"}
SCAN_KEEP_NAMES = {"README.md", "TEMPLATE.md"}
YAB_HOST = "github.com"
YAB_REPO = "lutsenko-yuriy/yuriys-agentic-boyz"
MAX_SCAN_BYTES = 1_000_000
TEMPLATE_MARKER = "<!-- yab:template -->"
ARTIFACTS = ["docs/TECH_STACK.md", "docs/CODE_STYLE.md", "docs/CONSTRAINTS.md"]
# The <...> tokens the shipped templates use (outside comments); a test keeps this in sync with the templates.
TEMPLATE_TOKENS = [
    "<language>", "<version>", "<e.g. application code, scripts>", "<framework or key library, with a link>",
    "<target platforms, runtimes or deployment environments>", "<tool>", "<service>", "<style guide link>",
    "<e.g. team size, who reviews, what support capacity exists>",
    "<e.g. pre-launch vs. in production; what to optimise for>",
    "<e.g. available devices, test environments, access limits>",
    "<e.g. cost ceilings, licensing, privacy or regulatory rules>",
]
REQUIRED_PROJECT_FIELDS = ["name", "description", "issue_prefix"]
NOTES_DIR = "docs/knowledge/notes"
NOTES_SKIP = {"BOOKMARKS.md", "INDEX.md", "TEMPLATE.md"}
# placeholder -> [project] field; PM_TOOL is derived from [providers].pm. Others (FRAMEWORK, STACK, ...) belong to the
# tech-stack artifacts and are never filled by apply.
PLACEHOLDER_FIELDS = {
    "AI_COMMIT_TRAILER": "ai_commit_trailer", "AI_TOOL_CREDIT": "ai_tool_credit",
    "ARCHITECTURE_SUMMARY": "architecture_summary", "AVAILABLE_MODELS": "available_models",
    "EXPERIMENT_TOOL": "experiment_tool", "GIT_HOST": "git_host", "INTEGRATION_TEST_DIR": "integration_test_dir",
    "IN_QA_PATHS": "in_qa_paths", "ISSUE_PREFIX": "issue_prefix", "PM_PROJECT_URL": "pm_project_url",
    "PROJECT_DESCRIPTION": "description", "PROJECT_ID": "project_id", "PROJECT_NAME": "name",
    "TEAM_ID": "team_id", "TEST_COMMAND": "test_command", "TEST_HARNESS_CLASS": "test_harness_class",
    "TEST_HARNESS_FILE": "test_harness_file", "VERSION_FIELD": "version_field", "VERSION_FILE": "version_file",
}
LIST_FIELDS = {"available_models", "in_qa_paths"}
# Keys must be skill_router provider names (scripts/skill_router/providers): [providers].pm routes to that provider.
PM_TOOLS = {"linear": "Linear", "github": "GitHub Issues"}
PROJECT_KEYS = set(PLACEHOLDER_FIELDS.values()) | {"keep_licence"}
MCP_LINEAR = {"type": "http", "url": "https://mcp.linear.app/mcp"}
TOOLCHAINS = ["git", "gh", "ollama", "flutter", "dart", "node", "npm", "java", "gradle", "kotlinc", "cargo", "go", "ruby"]
ENV_KEY_RE = re.compile(r"(_KEY|_TOKEN|_SECRET|_PAT)$")
ENV_IGNORE_PREFIX = "CLAUDE_CODE_"


class OnboardError(Exception):
    pass


class Refused(OnboardError):
    """A deliberate refusal (exit 1), as opposed to a failure to run (exit 3)."""


def valid_prefix(prefix: str) -> bool:
    return bool(PREFIX_RE.match(prefix)) and prefix.upper() not in PREFIX_REJECT


def default_prefix(name: str) -> str:
    """Returns "" when no valid prefix can be derived, so the caller must ask."""
    words = re.findall(r"[A-Za-z0-9]+", name)
    if len(words) > 1:
        cand = "".join(w[0] for w in words).upper()[:10]
    else:
        word = words[0] if words else ""
        humps = re.findall(r"[A-Z]", word)
        cand = "".join(humps) if len(humps) > 1 and not word.isupper() else word[:3].upper()
    if valid_prefix(cand):
        return cand
    cand = re.sub(r"[^A-Za-z]", "", name)[:3].upper()
    return cand if valid_prefix(cand) else ""


def load_toml(path: Path) -> Dict[str, Any]:
    try:
        import tomllib
    except ImportError:
        sys.stderr.write("onboard: tomllib unavailable (Python < 3.11); use python3.11+, e.g. python3.12\n")
        raise SystemExit(2)
    with open(path, "rb") as f:
        return tomllib.load(f)


def _tool(cmd: List[str]) -> Optional[subprocess.CompletedProcess]:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None


def probe(run_tools: bool = True) -> Dict[str, Any]:
    """Env values are never read out. Toolchains are only located; ollama/gh run only when run_tools."""
    data: Dict[str, Any] = {
        "env_vars_set": sorted(
            k for k, v in os.environ.items() if v and ENV_KEY_RE.search(k) and not k.startswith(ENV_IGNORE_PREFIX)
        ),
        "toolchains": {t: shutil.which(t) is not None for t in TOOLCHAINS},
        "pythons_with_tomllib": [
            n for n in ("python3.11", "python3.12", "python3.13", "python3.14") if shutil.which(n)
        ],
        "ollama_models": None,
        "gh_authenticated": None,
    }
    if run_tools and shutil.which("python3"):  # bare python3 is not in the versioned list above
        res = _tool(["python3", "-c", "import tomllib"])
        if res is not None and res.returncode == 0:
            data["pythons_with_tomllib"].append("python3")
    if run_tools and data["toolchains"]["ollama"]:
        res = _tool(["ollama", "list"])
        if res is not None and res.returncode == 0:
            data["ollama_models"] = [ln.split()[0] for ln in res.stdout.splitlines()[1:] if ln.strip()]
    if run_tools and data["toolchains"]["gh"]:
        res = _tool(["gh", "auth", "status"])
        if res is not None:
            data["gh_authenticated"] = res.returncode == 0
    return data


def _git(root: Path, *args: str, allow_fail: bool = False, timeout: float = 10) -> str:
    # LC_ALL=C: callers match git's messages (e.g. "not a git repository"), which Homebrew git localises.
    env = dict(os.environ, LC_ALL="C")
    res = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, encoding="utf-8", errors="replace", timeout=timeout,
        env=env,
    )
    if res.returncode != 0:
        if allow_fail:
            return ""
        raise OnboardError("git %s failed in %s: %s" % (" ".join(args), root, res.stderr.strip()))
    return res.stdout.strip()


def _tracked_files(root: Path) -> List[str]:
    out = _git(root, "-c", "core.quotePath=false", "ls-files", "-z")
    return [f for f in out.split("\0") if f]


def _untracked_problem(root: Path, scan_content: bool = True) -> Optional[str]:
    """check and apply only see tracked files, so untracked ones must not let a project pass vacuously.

    Three cases: nothing tracked (bare `git init`); a required file untracked; any other untracked, non-ignored
    scanned file that still holds a placeholder (a retrofit where only some files were `git add`-ed).
    """
    tracked = set(_tracked_files(root))
    if not tracked:
        return "no files are tracked by git: run `git add -A && git commit -m 'Initial import'` first"
    loose = [rel for rel in ARTIFACTS + ["skill_router.toml"] if (root / rel).exists() and rel not in tracked]
    if loose:
        return "not tracked by git (git add them): %s" % ", ".join(loose)
    if scan_content:
        out = _git(root, "-c", "core.quotePath=false", "ls-files", "-z", "--others", "--exclude-standard")
        dirty = []
        for rel in sorted(f for f in out.split("\0") if f and _scanned(f)):
            try:
                text = _read_regular(root / rel)
            except (UnicodeDecodeError, OSError):
                continue
            if PLACEHOLDER_RE.search(text or ""):
                dirty.append(rel)
        if dirty:
            return "untracked files with {{...}} placeholders (git add and commit them): %s" % ", ".join(dirty)
    return None


def _read_regular(path: Path) -> Optional[str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SCAN_BYTES:
        return None
    return path.read_bytes().decode("utf-8")  # not read_text: that would turn CRLF into LF on a later rewrite


def _section(text: str, heading: str) -> str:
    m = re.search(r"^##\s+%s\s*$(.*?)(?=^##\s|\Z)" % re.escape(heading), text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""


def _strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def _template_tokens(text: str) -> List[str]:
    text = re.sub(r"^(```|~~~).*?^\1[^\n]*$|(`+)[^`].*?\2(?!`)", "", _strip_comments(text),
                  flags=re.DOTALL | re.MULTILINE)
    return [t for t in TEMPLATE_TOKENS if t in text]


def _languages(tech_stack: str) -> List[str]:
    lines = [ln.strip() for ln in _section(tech_stack, "Languages").splitlines() if ln.strip().startswith("|")]
    sep = next((i for i, ln in enumerate(lines) if re.fullmatch(r"\|[\s:|-]+\|?", ln)), None)
    rows = lines[sep + 1:] if sep is not None else []
    names = []
    for row in rows:
        cell = re.sub(r"[*`]|\(.*?\)", "", row.strip("|").split("|")[0])
        names.extend(n for n in (_lang_name(part) for part in re.split(r"[/,]", cell)) if n)
    return names


def _lang_name(part: str) -> str:
    """"Dart ^3.6.0" -> "Dart", "Python3.12" -> "Python", "Node v20 LTS" -> "Node"; a version-only cell -> ""."""
    words = re.sub(r"^[^A-Za-z.]+", "", part).split()
    name = " ".join(w for w in words if not re.match(r"^(?:[\^~<>=v]*\d|LTS$|[^\w.]+$)", w, re.IGNORECASE))
    name = re.sub(r"(?<=[A-Za-z+#])\d[\d.x]*\+?$", "", name)
    return name if re.match(r"\.[A-Z]|[A-Za-z]", name) else ""


def _mentions(text: str, word: str) -> bool:
    # +, # and - are part of a name ("C" is not "C++"); a trailing digit is a version ("C++17", "Python3").
    return re.search(r"(?<![\w+#-])%s(?![A-Za-z_+#-])" % re.escape(word), text) is not None


def _scanned(rel: str) -> bool:
    if rel in SCAN_SKIP_FILES:
        return False
    return not rel.startswith(SCAN_SKIP_DIRS) or (
        rel.startswith("docs/knowledge/") and rel.rsplit("/", 1)[-1] in SCAN_KEEP_NAMES
    )


def _remote_id(url: str) -> Optional[tuple]:
    """(host, path) for network URLs (scheme://… or scp-style user@host:path); local and file:// remotes give None."""
    m = re.match(
        r"^(?:(?:https?|ssh|git|git\+ssh|ssh\+git)://(?:[^@/]+@)?([^/:?#]+)(?::\d+)?/|(?:[^@/:\s]+@)?([^/:\s]*\.[^/:\s]+):)"
        r"/*([^?#]+)",
        url.strip(), re.IGNORECASE,
    )
    if not m:
        return None
    host = (m.group(1) or m.group(2)).lower()
    path = re.sub(r"\.git$", "", m.group(3).rstrip("/"), flags=re.IGNORECASE).lower()
    return {"ssh.github.com": "github.com"}.get(host, host), path


def _template_mode(root: Path, errors: List[str]) -> bool:
    """The sentinel only counts when origin is YAB; adopters commonly keep YAB as `upstream`, so other remotes don't.

    A plain `git clone` of YAB being turned into a new project looks like YAB until its origin changes; in a YAB fork
    a human marks with `mark --force` from a terminal.
    """
    sentinel = root / ".yab-template"
    if not sentinel.exists():
        return False
    fields = dict(ln.split("=", 1) for ln in sentinel.read_text(encoding="utf-8", errors="replace").splitlines() if "=" in ln)
    origin = _git(root, "remote", "get-url", "origin", allow_fail=True)
    if fields.get("repo", "").strip().lower() == YAB_REPO and _remote_id(origin) == (YAB_HOST, YAB_REPO):
        return True
    errors.append(
        ".yab-template present but origin is not %s/%s: delete it if this project was created from YAB "
        "(in a YAB fork, run `mark --force` from a terminal)" % (YAB_HOST, YAB_REPO)
    )
    return False


def _read_config(root: Path) -> tuple:
    path = root / "skill_router.toml"
    if not path.is_file():
        raise OnboardError("skill_router.toml missing")
    try:
        cfg = load_toml(path)
    except ValueError as e:
        raise OnboardError("skill_router.toml: %s" % e)
    project, providers = cfg.get("project", {}), cfg.get("providers", {})
    if not isinstance(project, dict) or not isinstance(providers, dict):
        raise OnboardError("skill_router.toml: [project] and [providers] must be tables")
    return project, providers


def _pm(providers: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """The normalised [providers].pm ("" when unset) and the error, if any; shared by check and apply."""
    raw = providers.get("pm", "")
    if not isinstance(raw, str):
        return "", "providers.pm must be a string"
    pm = raw.strip()
    if pm and pm not in PM_TOOLS:
        return pm, "providers.pm %r must be one of %s" % (pm, ", ".join(sorted(PM_TOOLS)))
    return pm, None


def _check_config(root: Path, errors: List[str]) -> str:
    if not (root / "skill_router.toml").is_file():
        errors.append("skill_router.toml missing")
        return ""
    project, providers = _read_config(root)
    for field in REQUIRED_PROJECT_FIELDS:
        if not str(project.get(field, "")).strip():
            errors.append("project.%s is empty" % field)
    prefix = str(project.get("issue_prefix", "")).strip()
    if prefix and not valid_prefix(prefix):
        errors.append("project.issue_prefix %r is invalid (letters/digits, 2-10 chars, not N/A)" % prefix)
    pm, pm_error = _pm(providers)
    if pm_error:
        errors.append(pm_error)
    elif not pm:
        errors.append("providers.pm is empty")
    elif pm == "linear" and not str(project.get("project_id", "")).strip():
        errors.append("project.project_id is empty (required when providers.pm is linear; "
                      "move a legacy [linear].project_id there)")
    elif pm == "linear" and re.match(r"none\b", str(project.get("project_id", "")).strip(), re.I):
        errors.append("project.project_id must be a real id when providers.pm is linear, not 'none'")
    return prefix


def check(root: Path) -> Dict[str, Any]:
    """In template mode (YAB itself) unfilled placeholders, template artifacts and empty config are expected."""
    errors: List[str] = []
    template_mode = _template_mode(root, errors)
    untracked = _untracked_problem(root, scan_content=not template_mode)
    if untracked:
        errors.append(untracked)
    warnings: List[str] = []
    placeholders: Dict[str, List[str]] = {}
    for rel in _tracked_files(root):
        if not _scanned(rel):
            continue
        try:
            text = _read_regular(root / rel)
        except (UnicodeDecodeError, OSError):
            continue
        found = sorted(set(PLACEHOLDER_RE.findall(text or "")))
        if found:
            placeholders[rel] = found
    if placeholders and not template_mode:
        errors.append("%d file(s) still contain {{...}} placeholders" % len(placeholders))
    texts = {}
    for rel in ARTIFACTS:
        p = root / rel
        if not p.is_file():
            errors.append("%s missing" % rel)
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            errors.append("%s unreadable: %s" % (rel, e))
            continue
        if TEMPLATE_MARKER not in text:
            texts[rel] = text
            tokens = _template_tokens(text)
            if tokens:
                errors.append("%s still contains <...> template tokens (e.g. %s)" % (rel, tokens[0]))
        elif not template_mode:
            errors.append("%s is still a template" % rel)
    config_errors: List[str] = []
    prefix = _check_config(root, config_errors)
    if not template_mode:
        errors.extend(config_errors)
    if "docs/TECH_STACK.md" in texts:
        langs = _languages(texts["docs/TECH_STACK.md"])
        if not langs:
            errors.append("docs/TECH_STACK.md has no ## Languages table rows")
        base = _strip_comments(_section(texts.get("docs/CODE_STYLE.md", ""), "Base standard"))
        for lang in langs if "docs/CODE_STYLE.md" in texts else []:
            if not _mentions(base, lang):
                errors.append("CODE_STYLE Base standard does not cover TECH_STACK language %s" % lang)
    notes = root / NOTES_DIR
    if prefix and valid_prefix(prefix) and notes.is_dir():
        pat = re.compile(r"^%s-\d+" % re.escape(prefix))
        for n in sorted(notes.glob("*.md")):
            if n.name not in NOTES_SKIP and not pat.match(n.name):
                warnings.append("note %s does not match prefix %s-N" % (n.name, prefix))
    return {
        "ok": not errors,
        "template_mode": template_mode,
        "errors": errors,
        "warnings": warnings,
        "placeholders": placeholders,
    }


def _values(project: Dict[str, Any], pm: str) -> Dict[str, str]:
    """Non-empty placeholder values only: an empty one must stay a placeholder so `check` still reports it."""
    values: Dict[str, str] = {}
    for name, field in PLACEHOLDER_FIELDS.items():
        raw = project.get(field, "")
        if field in LIST_FIELDS and isinstance(raw, list) and all(isinstance(i, str) for i in raw):
            raw = ", ".join(i.strip() for i in raw if i.strip())
        if not isinstance(raw, str):
            raise OnboardError("skill_router.toml: project.%s must be a string" % field)
        raw = raw.strip()
        if "\n" in raw or "\r" in raw:
            raise OnboardError("skill_router.toml: project.%s must be a single line" % field)
        if field == "issue_prefix" and raw and not valid_prefix(raw):
            raise OnboardError("skill_router.toml: project.issue_prefix %r is invalid (letters/digits, 2-10 chars, not N/A)" % raw)
        if PLACEHOLDER_RE.search(raw):
            raise OnboardError("skill_router.toml: project.%s must not contain a {{PLACEHOLDER}}" % field)
        if raw:
            values[name] = raw
    if pm:
        values["PM_TOOL"] = PM_TOOLS[pm]
    return values


def _plan_mcp(root: Path, pm: str) -> Optional[str]:
    """None: leave .mcp.json alone. "": delete it. Otherwise its new text. The linear server iff pm == linear."""
    if not pm:
        return None
    path = root / ".mcp.json"
    exists = os.path.lexists(path)
    if exists and (path.is_symlink() or not path.is_file()):
        raise OnboardError(".mcp.json is not a regular file")
    try:
        cfg = json.loads(path.read_bytes().decode("utf-8")) if exists else {}
    except ValueError as e:
        raise OnboardError(".mcp.json is not valid JSON: %s" % e)
    servers = cfg.get("mcpServers", {}) if isinstance(cfg, dict) else None
    if not isinstance(servers, dict):
        raise OnboardError('.mcp.json must be an object with an object "mcpServers"')
    servers = dict(servers)
    if pm != "linear":
        servers.pop("linear", None)
    elif not isinstance(servers.get("linear"), dict):
        servers["linear"] = dict(MCP_LINEAR)
    new = {k: v for k, v in cfg.items() if k != "mcpServers"}
    if servers:
        new["mcpServers"] = servers
    if not new:
        return "" if exists else None
    return None if new == cfg else json.dumps(new, indent=2) + "\n"


def _write_atomic(path: Path, text: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".onboard-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(text.encode("utf-8"))
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def apply(root: Path) -> Dict[str, Any]:
    """Plan everything (reads, validation) before the first write; each file is then replaced atomically.

    Sentinel last: if a write fails midway, the files already written are whole and a re-run finishes the job.
    """
    if _template_mode(root, []):
        raise Refused("this is the YAB template itself (.yab-template, origin is YAB): apply would fill it in; refusing")
    untracked = _untracked_problem(root)
    if untracked:
        raise Refused(untracked)
    project, providers = _read_config(root)
    pm, pm_error = _pm(providers)
    if pm_error:
        raise OnboardError("skill_router.toml: %s" % pm_error)
    keep_licence = project.get("keep_licence", True)
    if not isinstance(keep_licence, bool):
        raise OnboardError("skill_router.toml: project.keep_licence must be true or false")
    values = _values(project, pm)
    warnings = ["skill_router.toml: unknown project.%s ignored" % k for k in sorted(set(project) - PROJECT_KEYS)]
    mcp = _plan_mcp(root, pm)
    edits: Dict[str, str] = {}
    unresolved: Dict[str, List[str]] = {}
    for rel in _tracked_files(root):
        if not _scanned(rel):
            continue
        try:
            text = _read_regular(root / rel)
        except (UnicodeDecodeError, OSError):
            continue
        if text is None:
            continue
        new = PLACEHOLDER_RE.sub(lambda m: values.get(m.group(0)[2:-2], m.group(0)), text)
        if new != text:
            edits[rel] = new
        left = sorted(set(PLACEHOLDER_RE.findall(new)))
        if left:
            unresolved[rel] = left
    for rel, text in edits.items():
        _write_atomic(root / rel, text)
    if mcp == "":
        os.unlink(root / ".mcp.json")
    elif mcp is not None:
        _write_atomic(root / ".mcp.json", mcp)
    license_path = root / "LICENSE"
    license_deleted = not keep_licence and (license_path.is_symlink() or license_path.is_file())
    if license_deleted:
        os.unlink(license_path)
    sentinel = root / ".yab-template"
    sentinel_deleted = os.path.lexists(sentinel) and not sentinel.is_dir()
    if sentinel_deleted:
        os.unlink(sentinel)
    return {
        "changed": sorted(edits),
        "unresolved": unresolved,
        "mcp": "deleted" if mcp == "" else "unchanged" if mcp is None else "written",
        "license_deleted": license_deleted,
        "sentinel_deleted": sentinel_deleted,
        "warnings": warnings,
    }


def repo_root(start: Path, timeout: float = 10) -> Path:
    """The resolved git toplevel containing `start`; raises OnboardError when it is not in a repo."""
    return Path(_git(start, "rev-parse", "--show-toplevel", timeout=timeout)).resolve()


def marker_path(root: Path, timeout: float = 10) -> Path:
    common = Path(_git(root, "rev-parse", "--git-common-dir", timeout=timeout))
    if not common.is_absolute():
        common = root / common
    return common.resolve() / "yab" / "onboarded"


def mark(root: Path, force: bool) -> int:
    # --force is for a human at a terminal; Claude's Bash has no TTY, so it cannot bypass the gate this way.
    if force and not (sys.stdin is not None and sys.stdin.isatty()):
        sys.stderr.write("onboard: --force is only allowed from an interactive terminal\n")
        return 1
    if not force and not check(root)["ok"]:
        sys.stderr.write("onboard: check is not clean; refusing to mark (fix issues, or --force)\n")
        return 1
    marker = marker_path(root)
    marker.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    sha = _git(root, "rev-parse", "--verify", "-q", "HEAD", allow_fail=True) or "unknown"
    fd, tmp = tempfile.mkstemp(dir=str(marker.parent))
    with os.fdopen(fd, "w") as f:
        f.write("onboarded=%s\nsha=%s\n" % (stamp, sha))
    os.replace(tmp, marker)
    print(marker)
    return 0


def _resolve_root(arg: Optional[str]) -> Path:
    start = Path(arg).resolve() if arg else Path(os.getcwd())
    top = repo_root(start)
    # git walks up to an enclosing repo; an explicit --root must be the toplevel itself.
    if arg and not os.path.samefile(str(top), str(start)):
        raise OnboardError("--root %s is not a repo toplevel (enclosing toplevel: %s)" % (start, top))
    return top


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        sys.stderr.write("onboard: %s\n" % message)
        raise SystemExit(3)


def main(argv: Optional[List[str]] = None) -> int:
    ap = _Parser(prog="onboard")
    ap.add_argument("--root", help="repo root (default: git toplevel of the current directory)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    sub.add_parser("check")
    sub.add_parser("apply")
    sub.add_parser("mark").add_argument("--force", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 3
    if args.cmd == "probe":
        print(json.dumps(probe(), indent=2))
        return 0
    try:
        root = _resolve_root(args.root)
        if args.cmd == "check":
            result = check(root)
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
        if args.cmd == "apply":
            print(json.dumps(apply(root), indent=2))
            return 0
        return mark(root, args.force)
    except Refused as e:
        sys.stderr.write("onboard: %s\n" % e)
        return 1
    except (OnboardError, OSError, subprocess.SubprocessError) as e:
        sys.stderr.write("onboard: %s\n" % e)
        return 3


if __name__ == "__main__":
    sys.exit(main())
