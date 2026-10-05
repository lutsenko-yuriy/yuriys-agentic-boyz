# Multi-Agent Project Template

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A GitHub template that bootstraps a **multi-skill AI workflow** (Linear or GitHub Issues for PM, GitHub as the Git host) for a new project.

## Skill workflow

```
Session start
  └─▶ summarize — presents backlog, asks "what goes into the next release?"

User-facing feature
  └─▶ analyze — plans analytics events and screen views, waits for approval
        └─▶ plan — produces implementation plan, waits for approval
               └─▶ implement — TDD, opens PR/MR
                      └─▶ review + audit — parallel review (architectural + runtime)
                             └─▶ ship — closes issues, regenerates docs, merges PR/MR
```

## Quick start

**Requires:** `git` and `python3` (3.11+ for onboarding's `check`/`apply`/`mark`), plus an authenticated `gh` if you use GitHub. Without `python3` the gate denies every tool call, and `/onboard` cannot fix that.

1. Click **Use this template** on GitHub, then clone your new repo.
2. Open Claude Code **from the repo root**, then run `/onboard`.

> **Launch from the repo root.** Claude Code reads the project `.claude/settings.json` only from the directory it starts in. Started from a subdirectory, the gate hooks do not load and the gate does not run.

## Onboarding

Until onboarding finishes, a gate (hooks in `.claude/settings.json`, `scripts/onboard/gate.py`) blocks writes outside a short allowlist, other skills, subagents, and most shell commands. `/onboard` runs inline and works within it.

It probes your machine, infers the stack from the repo, asks only what it cannot infer, and produces:

- `skill_router.toml` `[project]` (name, issue prefix, git host, test command, and so on) and `[providers].pm` (`linear` or `github`)
- `docs/TECH_STACK.md`, `docs/CODE_STYLE.md`, `docs/CONSTRAINTS.md`
- `docs/ARCHITECTURE.md`, the Common Commands in `AGENTS.md`, and the model tier mapping in `docs/MODEL_TIERS.md`
- optionally a gitignored `CLAUDE.local.md` with per-machine settings

`onboard.py apply` then fills the `[project]` values into the template placeholders in tracked files (except `scripts/onboard/`, `docs/knowledge/` and `docs/CHANGELOG.md`; re-running is safe), reconciles `.mcp.json` with your PM tool, deletes `LICENSE` if `keep_licence = false`, and removes the `.yab-template` sentinel. `onboard.py check` reports what is left; `onboard.py mark` refuses until it is clean.

### Steps you do yourself

The gate blocks these for the agent, so `/onboard` prints a ready-to-paste command and waits for "done":

- **Template origin:** if `origin` still points at this template, repoint it (`git remote set-url origin <your repo>`) or remove it.
- **Untracked files with placeholders:** `git add` them (staging is enough, no commit needed).
- **No git repo yet:** `git init` and make a first commit.
- **Maintaining a YAB fork:** `onboard.py mark --force`, from an interactive terminal.

### The onboarded marker

`mark` writes `yab/onboarded` inside the clone's git common dir (`git rev-parse --git-common-dir`). It is per clone and never committed, so each collaborator runs `/onboard` once; in an already-configured repo it only gives a short orientation and marks. Worktrees of one clone share it. Once present, the gate steps aside.

After onboarding, commit and push the result before collaborators clone; otherwise their `/onboard` runs the full configuration again. Then start with `/summarize`.

## What's included

- `skills/`: `configure` (onboard, calibrate, style, skill-creator, migrate-provider), `design` (brief, analyze, plan, research, experiment), `build` (implement), `verify` (review, audit, draft-scenarios), `manage` (summarize, ship, debrief, note, checkup)
- `.claude/commands/`: one slash-command stub per skill
- `styles/`: DETAILED, CONCISE, SCHEMATIC communication styles
- `scripts/onboard/`: onboarding helper, gate hooks and tests
- `AGENTS.md` / `CLAUDE.md`: orchestrator instructions, session start, workflow
- `docs/`: spec, architecture, tech stack, code style, constraints, backlog, changelog, versioning, model tiers

## Notes

- **`skills/` is committed** — skills are part of the project workflow; command stubs live in `.claude/commands/`.
- **No external PM tool required** — choose `github` as `[providers].pm` during `/onboard` to use GitHub Issues. It uses the `gh` CLI (`gh auth login`); no MCP.
- **PM tool auth is per-developer** — when using an external PM tool with an MCP server (e.g. Linear), each team member authenticates independently. No secrets are stored in the repo.
- **`CLAUDE.local.md` is gitignored** — put machine-specific paths and personal notes there.
- **Tool-agnostic by design** — skills describe what to do per PM tool (Linear or GitHub Issues, set by `[providers].pm`); the Git host is GitHub.
- **Model-agnostic by design** — skills declare `effort` and `reasoning` tiers instead of model names. The `calibrate` skill maps your available models to those tiers once, and the active mapping lives in `docs/MODEL_TIERS.md`.
- **Communication styles** — the `style` skill switches between DETAILED (full prose), CONCISE (lecture-note shorthand), and SCHEMATIC (TeX-like notation). Active style persists across sessions via `CLAUDE.local.md`.
