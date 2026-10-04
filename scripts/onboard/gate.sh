#!/bin/bash
# Hook wrapper for scripts/onboard/gate.py (HAB-278 WU4). bash 3.2-safe.
# Usage: gate.sh <EventName>   (the event is only used to pick the failure rule below)
# Claude Code fails OPEN on any exit code but 2, so a crashing/missing interpreter must be converted here:
#   PreToolUse (and unknown/no event): exit 2 = block.   SessionStart, UserPromptExpansion: exit 0 = fail open.
# gate.py's own output is trusted only if it exited 0/2 and stdout is empty or a JSON object.
event="${1:-}"
dir="$(cd "$(dirname "$0")" && pwd)"
py="${YAB_GATE_PYTHON:-python3}"

fail() {
  case "$event" in
    SessionStart|UserPromptExpansion) exit 0 ;;
  esac
  echo "Onboarding required — run /onboard (gate error: $1)" >&2
  exit 2
}

errf="$(mktemp 2>/dev/null)" || fail "mktemp"
out="$("$py" "$dir/gate.py" "$event" 2>"$errf")"
rc=$?
err="$(cat "$errf" 2>/dev/null)"
rm -f "$errf"

case "$rc" in
  0|2) ;;
  *) fail "gate.py exited $rc" ;;
esac
if [ -n "$out" ]; then
  case "$out" in
    "{"*"}") ;;
    *) fail "invalid gate output" ;;
  esac
  printf '%s\n' "$out"
fi
if [ "$rc" = 2 ]; then
  [ -n "$err" ] && printf '%s\n' "$err" >&2
  exit 2
fi
exit 0
