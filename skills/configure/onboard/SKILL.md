---
name: onboard
effort: FOCUSED
reasoning: ARCHITECTURAL
output_style: CONCISE
description: First-session onboarding. Probes the machine, collects project config into skill_router.toml, fills docs/TECH_STACK.md, docs/CODE_STYLE.md and docs/CONSTRAINTS.md by inferring the stack from the repo and confirming with the user, sets the model tier mapping, then runs the onboarding check and marks the clone onboarded. In an already-configured project it gives a one-screen orientation instead. Runs inline (no subagents) because the onboarding gate denies them.
---

This skill runs **inline in the main session**. While the clone is not onboarded the gate denies subagents, other skills, shell commands outside the allowlist and alterations outside the list below, so follow this file exactly and do not try to route around the gate.

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

Claude must be launched from the repo root: project hooks are read only from the launch directory, so a session started in a subdirectory is not gated.

Run `check` (exit 1 is normal here; read its JSON). State table:

| `.yab-template` | origin | Answer | `check` says | Do |
|---|---|---|---|---|
| absent | any | | no sentinel error | Configured (no errors, no placeholders): orientation (step 9), `mark`, stop. Otherwise step 3. |
| present | YAB | maintaining YAB | `template_mode` true, `ok` true | Orientation (step 9), then `mark` (it works in template mode); stop. |
| present | YAB | new project from the template | `template_mode` true | Human step A below. Re-run `check`: `template_mode` is now false with the sentinel error below. Continue at step 3; `apply` clears the sentinel. |
| present | not YAB, or none | | `template_mode` false, error ".yab-template present but origin is not ..." | Treat as an adopter: continue at step 3; `apply` clears the sentinel. If the user says this is a YAB fork for maintenance, Human step B, then stop. |

When `template_mode` is true, ask: "(a) maintaining YAB itself, or (b) a fresh project created from the template?"

For each human step, first get the absolute repo root with `git rev-parse --show-toplevel` and the interpreter from probe's `pythons_with_tomllib`, and print the command as one ready-to-paste line with both filled in (a new terminal window opens in the home directory, not the repo).

Human step A (new project): ask the user to open a separate terminal window and paste `cd <absolute repo root> && git remote set-url origin <their repo URL>` (or, if they have no remote repository yet, `cd <absolute repo root> && git remote remove origin`; origin then counts as none, the adopter row below), then say "done"; re-run check afterwards. The gate blocks it for you. With no origin, GitHub Issues as the PM tool cannot work until the user connects an origin later (a remote named origin pointing at their repository).
Human step C (untracked files with placeholders): when check or apply reports untracked files with placeholders, ask the user to open a separate terminal window and paste `cd <absolute repo root> && git add <the files it listed>`, then say "done"; staging is enough, no commit is needed. Re-run check (and apply) afterwards. The gate blocks it for you.
Human step B (YAB fork for maintenance): ask the user to open a separate terminal window and paste `cd <absolute repo root> && <interpreter> scripts/onboard/onboard.py mark --force` (it needs an interactive terminal), then say "done". Then verify the marker (below) and stop: do not run check or apply again, and do not go on to later steps.

To verify the marker after step B, run `git rev-parse --git-common-dir`, then `ls <git-common-dir>/yab/onboarded` with that output in place of the placeholder. If it is missing, ask the user to repeat step B.

Never run `git remote` yourself, touch the template sentinel yourself, or force the marker; do not use a `!` prefix for these (it may not be a terminal and may still pass through the gate).

### 3. Collect project config

Read `README.md` (unless it is still the YAB template README, titled "Multi-Agent Project Template": then do not infer the name or description from it, ask the user), the manifests and `git log --oneline -20` first and propose answers; ask only what cannot be inferred. Then Edit `skill_router.toml`:

- `[providers].pm`: exactly `"linear"` or `"github"` (GitHub Issues). It is mandatory and the only record of the PM tool. If the choice is Linear, check the Linear MCP is authenticated (ask the user to run `/mcp` if the read tools are unavailable) and look up the team and project with `mcp__linear__list_teams` and `mcp__linear__list_projects`.
- `[project]`: supply these keys. Prefix rule: letters and digits, 2-10 characters, starting with a letter, not `N/A`; default is the initials of a multi-word name, the capital letters of a CamelCase name, or the first 3 letters otherwise.

<!-- onboard:project-keys
name description architecture_summary issue_prefix git_host pm_project_url team_id project_id
experiment_tool available_models ai_commit_trailer ai_tool_credit test_command integration_test_dir
test_harness_file test_harness_class version_file version_field in_qa_paths keep_licence
-->

Rules: every key gets a concrete single-line value; never leave a key empty. An empty value keeps its placeholder, and some placeholders sit in files outside the list above (experiments, backlog, implement and review skills), so `check` could then never go clean. But a bare `none` is pasted verbatim by most consumers (commit trailers, PR bodies, the backlog link, project-config tables), so it is only allowed for these keys, whose consumers read it naturally (the experiment line in the experiments README; the team and project ids have no consumer outside the router, which uses the project id only for Linear):

<!-- onboard:none-ok
experiment_tool team_id project_id
-->

Every other key needs a real value:

<!-- onboard:real-value
name description architecture_summary issue_prefix git_host pm_project_url available_models
ai_commit_trailer ai_tool_credit test_command integration_test_dir test_harness_file test_harness_class
version_file version_field in_qa_paths
-->

Proposed defaults: `ai_commit_trailer` is the current agent's trailer line (for Claude, its `Co-Authored-By:` line from the session); `ai_tool_credit` is the matching credit line (for Claude Code, the "Generated with Claude Code" line with its link); `git_host` is the host of `origin` (with no origin, ask for `git_host` and `pm_project_url` instead of proposing them); `pm_project_url` is the Linear project URL, or the repo's `/issues` URL for GitHub Issues. For `integration_test_dir`, `test_harness_file`, `test_harness_class`, `version_file`, `version_field` and `in_qa_paths`, use what the repo really has; when it has none, use a phrase that reads correctly in the table, e.g. `none (no integration test harness)` or `none (no version file)`. `project_id` is a real id when `pm` is `"linear"`, else `none`; `available_models` is a comma-separated list and is what step 7 maps; `keep_licence` is `true` or `false` and `false` makes `apply` drop `LICENSE`.

### 4. Apply

Run `apply`. It substitutes the `[project]` values everywhere, reconciles `.mcp.json` with `pm` and clears the template sentinel. Report its `changed`, `unresolved` and `warnings`. Re-running is safe.

`apply` supplies every placeholder that has a `[project]` key. The one placeholder it never supplies is `CODE_STYLE` in `AGENTS.md`, which step 6 handles. If `unresolved` lists anything else, correct the value in `skill_router.toml` and re-run `apply`; values for `skills/shared/project-config.md` (test, version, QA fields) come from there too, so that file needs no hand edit.

### 5. The three artifacts

Follow `@skills/configure/onboard/resources/artifact-guide.md` for inference and for what a filled artifact looks like. For each of the three, show the user the proposed content and get a yes or corrections before writing:

- Write `docs/TECH_STACK.md`
- Write `docs/CODE_STYLE.md`
- Write `docs/CONSTRAINTS.md` (ask the four constraint questions; do not invent answers)

In all three, strip the `<!-- yab:template -->` marker line, every `<...>` token and the template's guidance comments. Every language in the TECH_STACK Languages table needs a Base standard entry in CODE_STYLE, with the language spelled identically (exact, case-sensitive). If no enforcer is configured for a language, say so instead of inventing one.

### 6. Architecture and agent docs

- Edit `docs/ARCHITECTURE.md`: the real directory tree, layers and dependencies, taken from the repo, go in place of the guidance comments. Keep it short and factual.
- Edit `AGENTS.md`: the Common Commands (`<test command>`, `<lint command>`, `<build command>`, `<install command>`) come from TECH_STACK's Tooling section, and a one-line summary of the Base standard takes the place of the `CODE_STYLE` placeholder line under "Code style".

### 7. Model tiers

`/calibrate` is blocked while gated, so do its work here. Read `skills/configure/calibrate/SKILL.md` and execute its steps 1 to 5 inline against `available_models`: skip 5a (command stubs live outside the writable list) and 6. Edit `docs/MODEL_TIERS.md` only. Do not run any shell command or fetch anything from calibrate (its LM Studio model-id lookup is denied while gated): ask the user for the model ids. Tell the user to run `/calibrate` later if they want the command stubs re-routed to the chosen models.

### 8. Per-machine settings (optional)

If the probe found tools the user will need (an interpreter path, a Flutter binary, an active communication style), offer to Write `CLAUDE.local.md` (gitignored; never put secrets in it). Skip if nothing applies.

### 9. Check, mark, orient

Run `check`. If `ok` is false, fix every error it lists (for untracked files with placeholders, Human step C in step 2) (and re-run `apply` if the config changed) until it is clean; surface warnings. Then run `mark`: it refuses unless `check` is clean, and forcing the marker is for the human only.

Then give the one-screen orientation per `@skills/configure/onboard/resources/orientation.md`, offer one optional Q&A turn, and hand off: the next step is the `summarize` skill (`/summarize`). Remind the user to commit and push the onboarding result before collaborators clone. In the already-configured path of step 2 the orientation is all there is.
