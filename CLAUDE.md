# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

{{PROJECT_NAME}} — {{PROJECT_DESCRIPTION}}

Full product specifications: @docs/PRODUCT_SPEC.md

## Documentation

| File | Purpose |
|---|---|
| @docs/PRODUCT_SPEC.md | What the app does — feature requirements |
| @docs/ARCHITECTURE.md | How the code is organised — layers, directory structure, dependencies |
| @docs/BACKLOG.md | Known issues and remaining work not yet released |
| @docs/CHANGELOG.md | Released version history |
| @docs/VERSIONING.md | Version numbering rules and CI/CD pipeline |
| @docs/ANALYTICS_EVENTS.md | Analytics event catalogue — events, screen views, and their properties |
| @docs/MODEL_TIERS.md | Effort Tier and Reasoning Depth vocabulary; active model → tier mapping |
| @docs/experiments/README.md | Experiment registry index — one `.md` file per experiment |
| CLAUDE.local.md | Local machine settings (binary paths, MCP auth, model tier mappings) — not committed |
| skills/configure/calibrate/SKILL.md | One-time setup: propose and approve the model → tier mapping |
| skills/configure/style/SKILL.md | Switch communication style: DETAILED, CONCISE, or SCHEMATIC |
| skills/manage/summarize/SKILL.md | Session-start: fetch and display the backlog |
| skills/manage/ship/SKILL.md | Post-merge housekeeping: close issues, update docs, bump version, merge |
| skills/design/analyze/SKILL.md | Analytics planning: identify events and screen views for a feature |
| skills/design/plan/SKILL.md | Implementation planning: structured plan from a PM issue |
| skills/build/implement/SKILL.md | TDD implementation and PR/MR |
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
4. The skill will summarise what has been done and what is remaining, then ask *"What goes into the next release?"*
5. Wait for the user's answer before proceeding.

## Workflow

Follow TDD: write or update tests **before** implementing the feature or fix. Red → Green → Refactor.

**Only one ticket may be in progress at a time.** Before picking up any new ticket, check the `## In Progress` section at the top of `docs/BACKLOG.md`. If a ticket is listed there, do not start new work until the current ticket is merged and the section is cleared.

**For features with user-visible screens or interactions**: invoke the `analyze` skill first to plan analytics before planning implementation:

```
Invoke the analyze skill for {{ISSUE_PREFIX}}-XX: <issue title>
```

The skill will identify trackable moments, propose events and screen views, flag PII concerns, update `docs/ANALYTICS_EVENTS.md`, and wait for approval. Pure infrastructure or CI changes with no user-facing screens skip this step.

**For large changes** (spanning multiple files, introducing new domain entities, new dependencies, or architectural shifts): invoke the `plan` skill to produce the implementation plan **before writing any code**:

```
Invoke the plan skill for {{ISSUE_PREFIX}}-XX: <issue title>
```

The skill will produce a structured plan (dependencies, models, UI changes, test strategy, ordered phases, work units) and wait for the user to approve or adjust it.

1. For features with user-facing screens/interactions, invoke `analyze` first and wait for approval.
2. For large changes, invoke `plan` and wait for plan approval.
3. Create a new feature branch from the latest `main` and switch to it before writing any code. Always include the issue number after `feature/`:
   ```
   git fetch origin
   git checkout -b feature/{{ISSUE_PREFIX}}-XX-<short-description> origin/main
   ```
   If the branch already exists, rebase it onto `origin/main` before writing any code (`git rebase origin/main`). This ensures the PR/MR diff contains only the new work. Mark the ticket as In Progress in `docs/BACKLOG.md`: replace the `_(nothing in progress)_` placeholder with a single bullet linking to the issue.
4. Write failing tests that describe the expected behaviour.
5. Implement the minimum code to make the tests pass.
6. Refactor if needed.
7. Run tests and linting — fix any failures before proceeding.
8. Apply formatting in a dedicated commit **before** the functional commit: run your stack's formatter and, if any files changed, stage and commit them separately with a `style:` prefix (e.g. `style: apply formatter`). This keeps style changes reviewable in isolation from logic changes.
9. Update documentation if affected by the changes:
    - `CLAUDE.md` — architecture, conventions, or workflow changed
    - `@docs/PRODUCT_SPEC.md` — functionality added, removed, or changed
    - `@docs/ARCHITECTURE.md` — code structure or dependencies changed
    - `@docs/VERSIONING.md` — CI/CD or versioning process impacted
10. **Keep the version in sync with `docs/CHANGELOG.md`.** Before committing, check that the version in the project's version file matches the latest `[X.Y.Z]` entry in `CHANGELOG.md`. If a new changelog entry was added in this PR, update the version accordingly. Do not touch the build number — CI manages it.
11. Commit all changes with a descriptive message.
12. Push to the remote and open a PR/MR — all in parallel:
    - Push the branch to the remote.
    - Open a PR/MR.
    - Invoke both review skills simultaneously once the PR/MR is open:
      - `review` for architectural review: `Invoke the review skill for PR/MR #<number>`.
      - `audit` for runtime/launch/migration review: `Invoke the audit skill for PR/MR #<number>`.
    - Inform the user of the PR/MR URL.
13. Remind the user to compact the context after each commit to keep the conversation lean.
14. When the user approves the PR/MR, invoke `ship` **before merging**:
    ```
    Invoke the ship skill for PR/MR #<number>
    ```
    The skill closes the PM issues, adds a CHANGELOG entry, regenerates BACKLOG.md, bumps the version, commits onto the feature branch, pushes, and merges. No separate approval is needed for the version bump.
15. Clear the context after the PR/MR with the changes is merged.

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
