#!/bin/bash
# Hook wrapper for scripts/onboard/gate.py (HAB-278 WU4). bash 3.2-safe.
# Usage: gate.sh <EventName>   (the event is only used to pick the failure rule below)
# Claude Code fails OPEN on any exit code but 2, and also when a hook times out, so crashes, a missing interpreter and
# hangs are converted here:
#   PreToolUse (and unknown/no event): exit 2 = block.   SessionStart, UserPromptExpansion: exit 0 = fail open.
# gate.py signals a deliberate block with exit 10 (CPython itself exits 2 when gate.py is missing, so 2 is not
# trusted). Output is trusted only if it exited 0/10 and stdout is empty or a JSON object. The interpreter runs under
# a watchdog (macOS has no timeout(1)) that must stay below the hook's own `timeout` (5 s in settings).
event="${1:-}"
dir="$(cd "$(dirname "$0")" && pwd)"
py="${YAB_GATE_PYTHON:-python3}"
deadline="${YAB_GATE_DEADLINE:-3}"

fail() {
  case "$event" in
    SessionStart|UserPromptExpansion) exit 0 ;;
  esac
  echo "Onboarding required — run /onboard (gate error: $1)" >&2
  exit 2
}

tmpd="$(mktemp -d 2>/dev/null)" || fail "mktemp"
trap 'rm -rf "$tmpd"' EXIT
cat >"$tmpd/in"  # a backgrounded command gets /dev/null as stdin, so hand it the payload as a file

"$py" "$dir/gate.py" "$event" <"$tmpd/in" >"$tmpd/out" 2>"$tmpd/err" &
pid=$!
( sleep "$deadline"; kill -9 "$pid" 2>/dev/null ) >/dev/null 2>&1 &  # leftovers (a git child, the sleep) are harmless: no fds held
watcher=$!
wait "$pid" 2>/dev/null
rc=$?
{ kill "$watcher"; wait "$watcher"; } 2>/dev/null

case "$rc" in
  0|10) ;;
  *) fail "gate.py exited $rc" ;;
esac
out="$(cat "$tmpd/out")"
if [ -n "$out" ]; then
  case "$out" in
    "{"*"}") ;;
    *) fail "invalid gate output" ;;
  esac
  printf '%s\n' "$out"
fi
if [ "$rc" = 10 ]; then
  err="$(cat "$tmpd/err")"
  [ -n "$err" ] && printf '%s\n' "$err" >&2
  exit 2
fi
exit 0
