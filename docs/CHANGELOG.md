# Changelog

A record of all versioned releases. For planned work and known issues, see @docs/BACKLOG.md.

---

## [Unreleased]

### Added / Changed / Fixed
- HAB-278 WU1: onboard.py probe, check, and mark subcommands [wip]
- HAB-278 WU2: onboard.py apply subcommand and [project] config schema in skill_router.toml [wip]
- HAB-278 WU3: scripts/onboard/bash_policy.py — read-only Bash allowlist for the onboarding gate (pipes only; getopt-aware denial of write/exec flags; Python 3.9-safe) [wip]
- HAB-278 WU4: scripts/onboard/gate.py + gate.sh — onboarding gate hook dispatcher (PreToolUse/UserPromptExpansion/SessionStart; fail-closed for tools, fail-open for prompts, 3 s watchdog); not wired until WU7 (PR #18) [wip]
- HAB-278 WU5: TECH_STACK/CODE_STYLE/CONSTRAINTS templates (yab:template marker) + check token/cross-check hardening; audit/review skills reference them (PR #19) [wip]
- HAB-278 WU6: /onboard skill (inline; probe→config→apply→artifacts→model tiers→check/mark; human-only steps for template/fork) + skill/gate agreement tests; check rejects project_id 'none' for linear (PR #20) [wip]
- HAB-278 WU7: cutover — gate hooks wired in committed .claude/settings.json, .yab-template sentinel, setup.sh removed, CI test job; check/apply refuse untracked or uncommitted template files; no-.git deny hint (PR #21) [wip]
- HAB-278 WU8: README rewritten for /onboard (launch from repo root, gate, produced files, human steps, onboarded marker); README exemption removed from skill tests (PR #22) [wip]

---

<!-- This file is maintained by the Product Owner agent.
     New sections are prepended after each merged PR in the format:

## [X.Y.Z] — YYYY-MM-DD (PR #N merged)

### Added / Changed / Fixed
- ...
-->
