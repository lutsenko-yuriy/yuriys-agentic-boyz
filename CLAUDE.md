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
| @docs/ANALYTICS_EVENTS.md | Analytics event catalogue — events, screen views, and their properties (create if the project tracks analytics) |
| @docs/experiments/README.md | Experiment registry index — one `.md` file per experiment, tracking hypothesis, metrics, and decision |
| CLAUDE.local.md | Local machine settings (binary paths, MCP auth, etc.) — not committed |
| .claude/agents/code-reviewer.md | PR review agent — invoked automatically in workflow step 11 |
| .claude/agents/product-owner.md | Product Owner agent — invoked at session start, for analytics planning, and after PR merge |
| .claude/agents/tech-lead.md | Tech Lead agent — invoked for large changes to produce an implementation plan before coding starts |
| .claude/agents/developer.md | Developer agent — invoked to implement a Tech Lead work unit following TDD |

## Architecture

{{ARCHITECTURE_SUMMARY}}

Details and directory layout: @docs/ARCHITECTURE.md.

## Common Commands

<!-- Update these with the actual commands for your stack -->
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

1. Ensure the Linear MCP is authenticated. If `mcp__linear__*` tools are unavailable, use `/mcp` to trigger the OAuth flow — see `CLAUDE.local.md` for setup notes.
2. Invoke the `product-owner` agent: `Use the product-owner agent to present the current backlog from Linear`.
3. The Product Owner agent will summarise what has been done and what is remaining, then ask *"What goes into the next release?"*.
4. Wait for the user's answer before proceeding.

## Workflow

Follow TDD: write or update tests **before** implementing the feature or fix. Red → Green → Refactor.

**Only one ticket may be in progress at a time.** Before picking up any new ticket, check the `## In Progress` section at the top of `docs/BACKLOG.md`. If a ticket is listed there, do not start new work until the current ticket is merged and the section is cleared.

**For features with user-visible screens or interactions**: invoke the `product-owner` agent first for analytics planning before the Tech Lead:

```
Use the product-owner agent to plan analytics for {{LINEAR_ISSUE_PREFIX}}-XX: <issue title>
```

The Product Owner will propose which events and screen views to track, flag any PII concerns, update `docs/ANALYTICS_EVENTS.md`, and wait for approval. Pure infrastructure or CI changes with no user-facing screens skip this step.

**For large changes** (spanning multiple files, introducing new domain entities, new dependencies, or architectural shifts): invoke the `tech-lead` agent to produce the implementation plan **before writing any code**:

```
Use the tech-lead agent to plan {{LINEAR_ISSUE_PREFIX}}-XX: <issue title>
```

The Tech Lead will produce a structured plan (dependencies, models, UI changes, test strategy, ordered phases, Developer work units) and wait for the user to approve or adjust it.

1. For features with user-facing screens/interactions, invoke the product-owner agent for analytics planning first and wait for approval.
2. For large changes, invoke the tech-lead agent and wait for plan approval.
3. Create a new feature branch from the latest `main` and switch to it before writing any code. Always include the Linear ticket number after `feature/`:
   ```
   git fetch origin
   git checkout -b feature/{{LINEAR_ISSUE_PREFIX}}-XX-<short-description> origin/main
   ```
   If the branch already exists, rebase it onto `origin/main` before writing any code (`git rebase origin/main`). This ensures the PR diff contains only the new work. Mark the ticket as In Progress in `docs/BACKLOG.md`: replace the `_(nothing in progress)_` placeholder with a single bullet linking to the issue (same format as in the milestone sections).
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
12. Push to the remote and open a PR — all in parallel:
    - Push the branch to the remote.
    - Open a PR.
    - Request reviews in parallel once the PR is open (both agents are independent — launch them simultaneously):
      - If `.claude/agents/tech-lead.md` exists, invoke it for an architectural review: `Use the tech-lead agent to review PR #<number>`.
      - If `.claude/agents/code-reviewer.md` exists, invoke it for a runtime/launch/migration review: `Use the code-reviewer agent to review PR #<number>`.
      - If neither agent exists, request a review from the user directly.
    - Inform the user of the PR URL.
13. Remind the user to compact the context after each commit to keep the conversation lean.
14. When the user approves the PR, invoke the `product-owner` agent **before merging**:
    ```
    Use the product-owner agent to prepare PR #<number> for merge: close the Linear issues, add a CHANGELOG entry, regenerate BACKLOG.md (restore the In Progress section to "_(nothing in progress)_" and remove the ticket from its milestone's remaining-work list), bump the version, commit everything onto the feature branch, push, then merge the PR.
    ```
    The housekeeping commits land on the feature branch so the squash merge captures them. No separate approval is needed for the version bump.
15. Clear the context after the PR with the changes is merged.

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
