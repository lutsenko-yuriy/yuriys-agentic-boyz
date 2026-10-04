# Changelog

A record of all versioned releases. For planned work and known issues, see @docs/BACKLOG.md.

---

## [Unreleased]

### Added / Changed / Fixed
- HAB-278 WU1: onboard.py probe, check, and mark subcommands [wip]
- HAB-278 WU2: onboard.py apply subcommand and [project] config schema in skill_router.toml [wip]
- HAB-278 WU3: scripts/onboard/bash_policy.py — read-only Bash allowlist for the onboarding gate (pipes only; getopt-aware denial of write/exec flags; Python 3.9-safe) [wip]
- HAB-278 WU4: scripts/onboard/gate.py + gate.sh — onboarding gate hook dispatcher (PreToolUse/UserPromptExpansion/SessionStart; fail-closed for tools, fail-open for prompts, 3 s watchdog); not wired until WU7 (PR #18) [wip]

---

<!-- This file is maintained by the Product Owner agent.
     New sections are prepended after each merged PR in the format:

## [X.Y.Z] — YYYY-MM-DD (PR #N merged)

### Added / Changed / Fixed
- ...
-->
