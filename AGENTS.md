# Agent Guidelines

This file provides guidance to AI coding agents (Claude Code, Codex, Cursor, OpenCode, etc.) working with code in this repository.

## Project Overview

{{PROJECT_NAME}} — {{PROJECT_DESCRIPTION}}

Full product specifications: docs/PRODUCT_SPEC.md

## Documentation

| File | Purpose |
|---|---|
| docs/PRODUCT_SPEC.md | What the app does — feature requirements |
| docs/ARCHITECTURE.md | How the code is organised — layers, directory structure, dependencies |
| docs/BACKLOG.md | Known issues and remaining work not yet released |
| docs/CHANGELOG.md | Released version history |
| docs/VERSIONING.md | Version numbering rules and CI/CD pipeline |
| docs/ANALYTICS_EVENTS.md | Analytics event catalogue — events, screen views, and their properties |
| docs/MODEL_TIERS.md | Effort Tier and Reasoning Depth vocabulary; active model → tier mapping |
| docs/experiments/README.md | Experiment registry index — one `.md` file per experiment |
| docs/knowledge/README.md | Project knowledge base — vault layout, per-ticket file format, how `/note` and `/debrief` write entries |
| docs/knowledge/decisions/README.md | ADR registry index — one `.md` file per standing decision, discoverable independent of the ticket that produced it |
| docs/workflows/FEATURE.md | Step-by-step feature development workflow — TDD cycle, branching, PR/MR, ship, and ticket state rules |
| docs/workflows/TROUBLESHOOT.md | Reactive workflow for bugs, CI failures, and infrastructure issues — investigate, ticket, fix, ship |
| docs/workflows/RESEARCH.md | Step-by-step workflow for research-only tickets — alternatives survey, constraint evaluation, debrief |
| docs/workflows/POSTMORTEM.md | Post-fix root-cause investigation workflow — reconstructing when/why a shipped bug was introduced, after `TROUBLESHOOT.md` produced the fix |
| docs/workflows/MULTI_WU.md | Multi-WU ticket appendix to `FEATURE.md` — WU-splitting guidelines, pre-implementation WU types, branch/PR-per-WU rules, WU cycle |
| CLAUDE.local.md | Local machine settings (binary paths, MCP auth, model tier mappings) — not committed |
| skills/configure/calibrate/SKILL.md | One-time setup: propose and approve the model → tier mapping |
| skills/configure/migrate-provider/SKILL.md | Switch a tool role (pm, vcs) to a different provider without changing skill files |
| skills/configure/skill-creator/SKILL.md | Two-mode skill: create a new skill (guided wizard) or refactor an existing one into lean SKILL.md + resources |
| skills/configure/style/SKILL.md | Switch communication style: DETAILED, CONCISE, or SCHEMATIC |
| skills/manage/summarize/SKILL.md | Session-start: fetch and display the backlog |
| skills/manage/ship/SKILL.md | Post-merge housekeeping: close issues, update docs, bump version, merge |
| skills/manage/debrief/SKILL.md | Post-ticket retrospective: structured dialog → workflow improvements + knowledge base entry |
| skills/manage/note/SKILL.md | Capture a quick observation mid-session into `docs/knowledge/notes/` |
| skills/manage/checkup/SKILL.md | Two-tier periodic code-quality checkup (light monthly / heavy quarterly) — walks 9 non-mechanical dimensions, fixes inline or defers findings to a ledger with deadlines |
| skills/design/analyze/SKILL.md | Analytics planning: identify events and screen views for a feature |
| skills/design/brief/SKILL.md | Feature intake: clarifying dialog → scoped PM ticket + glossary update. When called with an existing ticket ID, checks if the description is still current and offers to revise it. |
| skills/design/plan/SKILL.md | Implementation planning: structured plan from a PM issue |
| skills/design/research/SKILL.md | Literature research: thesis/antithesis/synthesis for a claim, or a scoping map for a bare topic — cited evidence, single synthesis pass |
| skills/build/implement/SKILL.md | TDD implementation and PR/MR |
| skills/verify/draft-scenarios/SKILL.md | Pre-implementation scenario drafting: write red integration test stubs from the ticket spec |
| skills/verify/review/SKILL.md | Architectural PR/MR review |
| skills/verify/audit/SKILL.md | Runtime and migration PR/MR review |

## Architecture

{{ARCHITECTURE_SUMMARY}}

Details and directory layout: @docs/ARCHITECTURE.md.

## Common Commands

- **Run tests:** `<test command>`
- **Lint:** `<lint command>`
- **Build:** `<build command>`
- **Install dependencies:** `<install command>`

## Code style

{{CODE_STYLE}}

## Versioning

Update the version name whenever a new `CHANGELOG.md` entry is added — no separate approval needed.
CI handles build numbers automatically — do not touch.
Details: @docs/VERSIONING.md

## Session start

At the beginning of every new session, before doing anything else:

1. Ensure your PM tool MCP (if used) is authenticated. If MCP tools for your PM tool are unavailable, run `/mcp` to trigger the OAuth flow — see `CLAUDE.local.md` for setup notes.
2. Check `CLAUDE.local.md` for an `## Active communication style` section and silently load that style (see `styles/`). If absent, each skill will use its own `output_style` — no global default.
3. Invoke the `summarize` skill to present the current backlog.
4. Run `scripts/checkup/due.py --format=session`. If it reports a tier as due, recommend running `/checkup` before picking up a new ticket, alongside the backlog summary.
5. The skill will summarise what has been done and what is remaining, then ask *"What goes into the next release? Pick an existing ticket or describe something new."*
6. Wait for the user's answer before proceeding. If the user wants to describe something new, invoke the `brief` skill before any planning begins.

## Workflow

@docs/workflows/FEATURE.md

Reactive work (bugs, CI failures, regressions, infrastructure breakage) uses
`docs/workflows/TROUBLESHOOT.md` instead of the above. Research-only tickets use
`docs/workflows/RESEARCH.md`. Post-fix root-cause investigation (reconstructing when/why a
shipped bug was introduced, after `TROUBLESHOOT.md` produced the fix) uses
`docs/workflows/POSTMORTEM.md`. Read whichever one applies by path when its trigger condition
is met — they are not preloaded every session.

## Experiments

Product experiments are tracked in `docs/experiments/`. The registry README (`docs/experiments/README.md`) contains the index table; each individual experiment has its own file named `EXP-NNN-<short-name>.md` following `docs/experiments/TEMPLATE.md`.

When starting an experiment:
1. Pick the next sequential `EXP-NNN` ID from the index table in `docs/experiments/README.md`.
2. Copy `docs/experiments/TEMPLATE.md` to `docs/experiments/EXP-NNN-<short-name>.md`.
3. Fill in the hypothesis, setup, and metrics sections. Leave Decision and Learnings blank.
4. Add a row to the index table with status `running`.

When an experiment concludes (status changes to `won`, `lost`, or `abandoned`):
1. Update the experiment file with the final decision and learnings.
2. Update the index row in `docs/experiments/README.md` with the primary metric result and decision date.

The registry must be kept up to date so experiment outcomes are never lost.
