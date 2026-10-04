---
name: onboard
effort: FOCUSED
reasoning: ARCHITECTURAL
output_style: CONCISE
description: First-session onboarding. Probes the machine, collects project config into skill_router.toml, fills docs/TECH_STACK.md, docs/CODE_STYLE.md and docs/CONSTRAINTS.md by inferring the stack from the repo and confirming with the user, sets the model tier mapping, then runs the onboarding check and marks the clone onboarded. In an already-configured project it gives a one-screen orientation instead. Runs inline (no subagents) because the onboarding gate denies them.
---

This skill runs **inline in the main session**. While the clone is not onboarded the gate denies subagents, other skills, shell commands outside the allowlist and edits outside the list below, so follow this file exactly and do not try to route around the gate.

<!-- onboard:tools Read, Glob, Grep, Edit, Write, Bash, AskUserQuestion, ToolSearch, TodoWrite -->

Ask one question at a time with `AskUserQuestion`. Respect the active communication style from `CLAUDE.local.md`.

## What this skill may change

Only these files. Everything else is filled by `onboard.py apply`.

<!-- onboard:writes -->
- `skill_router.toml`
- `docs/TECH_STACK.md`
- `docs/CODE_STYLE.md`
- `docs/CONSTRAINTS.md`
- `docs/ARCHITECTURE.md`
- `AGENTS.md`
- `docs/MODEL_TIERS.md`
- `CLAUDE.local.md`
<!-- /onboard:writes -->

## Commands

Only these commands are allowed while gated. Use exactly this form, with no flags. The human-only commands are in step 2.

`probe` works on any Python 3. `check`, `apply` and `mark` need Python 3.11+: use an interpreter named in the probe's `pythons_with_tomllib` (a versioned name such as `python3.12`, or plain `python3`), or the absolute path `CLAUDE.local.md` gives. Below, `python3.12` stands for that interpreter.

```bash
python3 scripts/onboard/onboard.py probe
python3.12 scripts/onboard/onboard.py check
python3.12 scripts/onboard/onboard.py apply
python3.12 scripts/onboard/onboard.py mark
```

Read-only inspection (`ls`, `cat`, `git log`, `git ls-files`, `grep`) is fine. `flutter --version`, builds and installs are not: infer the stack from manifests instead.

## Steps

### 1. Probe the machine

Run `probe` with plain `python3`. Note `pythons_with_tomllib` (if empty, stop and ask the user to install Python 3.11+), which toolchains exist, `gh_authenticated`, `ollama_models`, and which `env_vars_set` names exist (names only; never ask the user to paste a secret).

### 2. Detect the mode

Run `check` (exit 1 is normal here; read its JSON). State table:

| `.yab-template` | origin | Answer | `check` says | Do |
|---|---|---|---|---|
| absent | any | | no sentinel error | Configured (no errors, no placeholders): orientation (step 9), `mark`, stop. Otherwise step 3. |
| present | YAB | maintaining YAB | `template_mode` true, `ok` true | Orientation (step 9), then `mark` (it works in template mode); stop. |
| present | YAB | new project from the template | `template_mode` true | Ask the user to run `! git remote set-url origin <their repo URL>` themselves (the gate blocks it for you; `!` runs as the user). Re-run `check`: `template_mode` is now false with the sentinel error below. Continue at step 3; `apply` removes the sentinel. |
| present | not YAB, or none | | `template_mode` false, error ".yab-template present but origin is not ..." | Treat as an adopter: continue at step 3; `apply` removes the sentinel. If the user says this is a YAB fork for maintenance, ask them to run `! python3.12 scripts/onboard/onboard.py mark --force` in their own terminal (it needs an interactive terminal) and stop. |

When `template_mode` is true, ask: "(a) maintaining YAB itself, or (b) a fresh project created from the template?". Never run `git remote`, delete `.yab-template` or force the marker yourself.

### 3. Collect project config

Read `README.md`, the manifests and `git log --oneline -20` first and propose answers; ask only what cannot be inferred. Then Edit `skill_router.toml`:

- `[providers].pm`: exactly `"linear"` or `"github"` (GitHub Issues). It is mandatory and the only record of the PM tool. If the choice is Linear, check the Linear MCP is authenticated (ask the user to run `/mcp` if the read tools are unavailable) and look up the team and project with `mcp__linear__list_teams` and `mcp__linear__list_projects`.
- `[project]`: fill these keys. Prefix rule: letters and digits, 2-10 characters, starting with a letter, not `N/A`; default is the initials of a multi-word name, the capital letters of a CamelCase name, or the first 3 letters otherwise.

<!-- onboard:project-keys
name description architecture_summary issue_prefix git_host pm_project_url team_id project_id
experiment_tool available_models ai_commit_trailer ai_tool_credit test_command integration_test_dir
test_harness_file test_harness_class version_file version_field in_qa_paths keep_licence
-->

Rules: every key gets a concrete single-line value; never leave a key empty. Where a key does not apply, enter the literal `none`. An empty value keeps its placeholder, and some placeholders sit in files outside the list above (experiments, backlog, implement and review skills), so `check` could then never go clean. `project_id` is a real id when `pm` is `"linear"` (`none` for `"github"`); `available_models` is a comma-separated list and is what step 7 maps; `keep_licence` is `true` or `false` and `false` makes `apply` delete `LICENSE`.

### 4. Apply

Run `apply`. It substitutes the `[project]` values everywhere, reconciles `.mcp.json` with `pm` and removes the template sentinel. Report its `changed`, `unresolved` and `warnings`. Re-running is safe.

`apply` fills every placeholder that has a `[project]` key. The one placeholder it never fills is `CODE_STYLE` in `AGENTS.md`, which step 6 replaces. If `unresolved` lists anything else, correct the value in `skill_router.toml` and re-run `apply`; values for `skills/shared/project-config.md` (test, version, QA fields) come from there too, so that file needs no hand edit.

### 5. Fill the three artifacts

Follow `@skills/configure/onboard/resources/artifact-guide.md` for inference and for what a filled artifact looks like. For each of the three, show the user the proposed content and get a yes or corrections before writing:

- Write `docs/TECH_STACK.md`
- Write `docs/CODE_STYLE.md`
- Write `docs/CONSTRAINTS.md` (ask the four constraint questions; do not invent answers)

When writing: remove the `<!-- yab:template -->` marker line, every `<...>` token and the template's guidance comments. Every language in the TECH_STACK Languages table needs a Base standard entry in CODE_STYLE, with the language spelled identically (exact, case-sensitive). If no enforcer is configured for a language, say so instead of inventing one.

### 6. Architecture and agent docs

- Edit `docs/ARCHITECTURE.md`: replace the guidance comments with the real directory tree, layers and dependencies, taken from the repo. Keep it short and factual.
- Edit `AGENTS.md`: fill the Common Commands (`<test command>`, `<lint command>`, `<build command>`, `<install command>`) from TECH_STACK's Tooling section, and replace the `CODE_STYLE` placeholder line under "Code style" with a one-line summary of the Base standard.

### 7. Model tiers

`/calibrate` is blocked while gated, so do its work here. Read `skills/configure/calibrate/SKILL.md` and execute its steps 1 to 5 inline against `available_models`: skip 5a (command stubs live outside the writable list) and 6. Edit `docs/MODEL_TIERS.md` only. Do not run any shell command or fetch anything from calibrate (its LM Studio model-id lookup is denied while gated): ask the user for the model ids. Tell the user to run `/calibrate` later if they want the command stubs re-routed to the chosen models.

### 8. Per-machine settings (optional)

If the probe found tools the user will need (an interpreter path, a Flutter binary, an active communication style), offer to Write `CLAUDE.local.md` (gitignored; never put secrets in it). Skip if nothing applies.

### 9. Check, mark, orient

Run `check`. If `ok` is false, fix every error it lists (and re-run `apply` if the config changed) until it is clean; surface warnings. Then run `mark`: it refuses unless `check` is clean, and forcing the marker is for the human only.

Then give the one-screen orientation per `@skills/configure/onboard/resources/orientation.md`, offer one optional Q&A turn, and hand off: the next step is the `summarize` skill (`/summarize`). In the already-configured path of step 1 the orientation is all there is.
