#!/usr/bin/env python3
"""Onboarding gate: a Claude Code hook dispatcher (HAB-278 WU4). Stdlib only, Python 3.9 compatible.

Reads one hook payload from stdin and keys on `hook_event_name`. Once the clone is onboarded (the per-clone marker
written by `onboard.py mark`, located with onboard.marker_path) every event is a no-op: exit 0, no output. Before that:

    SessionStart         additionalContext: "Onboarding required - run /onboard"
    UserPromptExpansion  slash commands: allow `onboard` and built-ins, block every other command (BLOCK_EXIT)
    PreToolUse           Skill: only `onboard`; Agent: deny; Edit/Write/MultiEdit/NotebookEdit: only BOOTSTRAP_PATHS
                         (realpath, contained in the repo root); Bash: bash_policy.is_allowed; mcp__*: read verbs
                         only; read-only built-ins pass; anything else is denied (fail closed)

"Allowed" is exit 0 with no output, never an `allow` decision, so normal permission prompts still apply.

Claude Code fails OPEN on every hook exit code except 2, so failure handling is explicit and per event:
PreToolUse fails closed (deny); SessionStart and UserPromptExpansion fail open, so /onboard can never be locked out.
gate.sh enforces the same rule when this process itself dies, and maps BLOCK_EXIT to exit 2. Both take the event
name as argv[1], used only when the payload is unreadable.

A hang also fails OPEN (Claude Code lets the call through when a hook times out), so gate.sh runs the interpreter
under a 3 s watchdog (YAB_GATE_DEADLINE) and the gate's git calls time out after 2 s; the hook `timeout` is only a
backstop and must stay above 3.

Known residual: the MCP rule trusts tool *names* (a `get_or_create_*` tool would pass; the payload carries no
readOnlyHint). Mitigated because the agent cannot add MCP servers while gated.

Wired in the committed .claude/settings.json (each row `"timeout": 5`; command is gate.sh with the event as argv[1]):
    SessionStart (matcher startup), UserPromptExpansion, PreToolUse (no matcher)

Known residual: project settings are only read from the launch directory, so launching Claude from a subdirectory
of the repo skips the gate entirely; launch Claude from the repo root.

Known residual: whether PreToolUse fires for user `!` shell commands is not relied on; the human-only steps in
/onboard use a separate terminal.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if __package__ in (None, ""):  # run as a script: scripts/onboard is on sys.path, the repo root is not
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.onboard import bash_policy, onboard

Result = Tuple[int, str, str]  # exit code, stdout, stderr

NEEDS_ONBOARDING = "Onboarding required — run /onboard"
ONBOARD_SKILL = "onboard"
# The artifacts /onboard writes; everything else is filled by `onboard.py apply`. Single source of truth.
BOOTSTRAP_PATHS = tuple(onboard.ARTIFACTS) + (
    "docs/ARCHITECTURE.md", "AGENTS.md", "skill_router.toml", "skills/shared/project-config.md",
    "skills/shared/pm-tool-mapping.md", "docs/MODEL_TIERS.md", "CLAUDE.local.md",
)
WRITE_TOOLS = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
MCP_READ_PREFIXES = ("get_", "list_", "search_", "extract_")
# Read-only or inert built-ins (AskUserQuestion and ToolSearch are needed by /onboard itself). Unknown tools are denied.
PASS_TOOLS = frozenset(
    "Read Glob Grep LS NotebookRead WebFetch WebSearch TodoWrite ToolSearch AskUserQuestion "
    "TaskCreate TaskGet TaskList TaskUpdate EnterPlanMode ExitPlanMode".split()
)
BUILTIN_SOURCE = "builtin"
FAIL_OPEN_EVENTS = frozenset({"SessionStart", "UserPromptExpansion"})

# gate.py's own "block" code. Not 2: CPython exits 2 itself (script not found, bad option), which gate.sh must not
# mistake for a deliberate block. gate.sh maps exactly this code to Claude Code's blocking exit 2.
BLOCK_EXIT = 10

# Well under gate.sh's 3 s watchdog and the 5 s hook timeout, so a slow git ends in the gate's own per-event rule.
GIT_TIMEOUT = 2

OK = (0, "", "")

NOT_A_REPO = "not a git repository"
NO_REPO_HINT = "not a git repository - run `git init && git add -A && git commit -m 'Initial import'` in a separate terminal in the project root, then /onboard"


def _deny(reason: str) -> Result:
    out = {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "%s: %s" % (NEEDS_ONBOARDING, reason),
    }}
    return 0, json.dumps(out), ""


def is_onboarded(root: Path) -> bool:
    return onboard.marker_path(root, timeout=GIT_TIMEOUT).is_file()


def _find_root(data: Dict[str, Any]) -> Path:
    """CLAUDE_PROJECT_DIR first: the payload cwd follows the Bash tool's `cd`, so a nested repo or non-git dir there
    would point the gate at the wrong marker. The payload cwd is then only a fallback (and resolves relative paths)."""
    cwd = data.get("cwd")
    candidates = [os.environ.get("CLAUDE_PROJECT_DIR"), cwd if isinstance(cwd, str) else None, os.getcwd()]
    error = None
    for start in candidates:
        if not start:
            continue
        try:
            return onboard.repo_root(Path(start), timeout=GIT_TIMEOUT)
        except (onboard.OnboardError, OSError) as exc:
            error = error or exc
    raise error or onboard.OnboardError("no repository found")


def bootstrap_target_allowed(root: Path, raw: Any, cwd: Path) -> bool:
    """realpath() resolves symlinks and `..` even for a not-yet-existing tail, so escapes cannot pass either check."""
    if not isinstance(raw, str) or not raw.strip() or "\0" in raw:
        return False
    target = os.path.realpath(os.path.join(str(cwd), raw))
    real_root = os.path.realpath(str(root))
    for rel in BOOTSTRAP_PATHS:
        # Resolve the parent directories but not the leaf: a bootstrap file that is itself a symlink resolves
        # elsewhere (outside the repo or to another file) and so never equals its own lexical location.
        allowed = os.path.join(os.path.realpath(os.path.dirname(os.path.join(real_root, rel))), os.path.basename(rel))
        if target == allowed and os.path.commonpath([real_root, allowed]) == real_root:
            return True
    return False


def _pre_tool_use(data: Dict[str, Any], root: Path) -> Result:
    name = data.get("tool_name")
    tool_input = data.get("tool_input")
    if not isinstance(name, str) or not isinstance(tool_input, dict):
        return _deny("malformed tool call")
    if name == "Skill":
        return OK if tool_input.get("skill") == ONBOARD_SKILL else _deny("only the onboard skill may run")
    if name == "Agent":
        return _deny("subagents are disabled; onboarding runs inline")
    if name in WRITE_TOOLS:
        cwd = Path(data["cwd"]) if isinstance(data.get("cwd"), str) and data["cwd"] else root
        if bootstrap_target_allowed(root, tool_input.get(WRITE_TOOLS[name]), cwd):
            return OK
        return _deny("%s may only change the onboarding artifacts" % name)
    if name == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str):
            return _deny("malformed Bash command")
        allowed, reason = bash_policy.is_allowed(command)
        return OK if allowed else _deny("Bash: %s" % reason)
    if name.startswith("mcp__"):
        parts = name.split("__", 2)  # mcp__<server>__<tool>; a tool name that itself contains "__" is ambiguous: deny
        if len(parts) == 3 and "__" not in parts[2] and parts[2].startswith(MCP_READ_PREFIXES):
            return OK
        return _deny("MCP tool %s is not read-only" % name)
    if name in PASS_TOOLS:
        return OK
    return _deny("tool %s is not allowed" % name)


def _prompt_expansion(data: Dict[str, Any]) -> Result:
    if data.get("expansion_type") != "slash_command":
        return OK
    # Built-ins (/mcp, /clear, ...) do not currently fire this event; the source check is defensive.
    if data.get("command_name") == ONBOARD_SKILL or data.get("command_source") == BUILTIN_SOURCE:
        return OK
    return BLOCK_EXIT, "", "%s (blocked /%s)\n" % (NEEDS_ONBOARDING, data.get("command_name"))


def decide(data: Dict[str, Any], event: str, root: Path) -> Result:
    if event == "SessionStart":
        out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": NEEDS_ONBOARDING}}
        return 0, json.dumps(out), ""
    if event == "UserPromptExpansion":
        return _prompt_expansion(data)
    if event == "PreToolUse":
        return _pre_tool_use(data, root)
    return OK


def _fail(event: Optional[str], why: str) -> Result:
    """Fail closed (PreToolUse and unknown) or open (SessionStart, UserPromptExpansion)."""
    if event in FAIL_OPEN_EVENTS:
        return 0, "", ""
    if event == "PreToolUse":
        return _deny("gate error (%s)" % why)
    return BLOCK_EXIT, "", "%s (gate error: %s)\n" % (NEEDS_ONBOARDING, why)


def run(stdin_text: str, fallback_event: Optional[str] = None) -> Result:
    event = fallback_event
    try:
        try:
            data = json.loads(stdin_text)
        except ValueError:
            data = None
        if not isinstance(data, dict):
            data = {}
        else:
            event = data.get("hook_event_name") if isinstance(data.get("hook_event_name"), str) else event
        try:
            root = _find_root(data)
        except onboard.OnboardError as exc:
            if event == "PreToolUse" and NOT_A_REPO in str(exc):
                return _deny(NO_REPO_HINT)
            raise
        if is_onboarded(root):
            return OK
        if not data:
            return _fail(event, "unreadable hook payload")
        return decide(data, event or "", root)
    except Exception as exc:  # noqa: BLE001 - the per-event failure rule must hold for any error
        return _fail(event, "%s: %s" % (type(exc).__name__, exc))


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        text = sys.stdin.read()
    except Exception:  # noqa: BLE001
        text = ""
    code, out, err = run(text, argv[0] if argv else None)
    if out:
        sys.stdout.write(out + "\n")
    if err:
        sys.stderr.write(err)
    return code


if __name__ == "__main__":
    sys.exit(main())
