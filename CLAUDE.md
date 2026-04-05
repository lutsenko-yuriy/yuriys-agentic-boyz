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
| CLAUDE.local.md | Local machine settings (binary paths, MCP auth, etc.) — not committed |
| .claude/agents/code-reviewer.md | PR review agent — invoked automatically in workflow step 11 |
| .claude/agents/product-owner.md | Product Owner agent — invoked at session start and after PR merge |
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

Version bumps require user approval before any change.
Details: @docs/VERSIONING.md

## Session start

At the beginning of every new session, before doing anything else:

1. Ensure the Linear MCP is authenticated. If `mcp__linear__*` tools are unavailable, use `/mcp` to trigger the OAuth flow — see `CLAUDE.local.md` for setup notes.
2. Invoke the `product-owner` agent: `Use the product-owner agent to present the current backlog from Linear`.
3. The Product Owner agent will summarise what has been done and what is remaining, then ask *"What goes into the next release?"*.
4. Wait for the user's answer before proceeding.

## Workflow

Follow TDD: write or update tests **before** implementing the feature or fix. Red → Green → Refactor.

**For large changes** (spanning multiple files, introducing new domain entities, new dependencies, or architectural shifts): invoke the `tech-lead` agent to produce the implementation plan **before writing any code**:

```
Use the tech-lead agent to plan {{LINEAR_ISSUE_PREFIX}}-XX: <issue title>
```

The Tech Lead will produce a structured plan (dependencies, models, UI changes, test strategy, ordered phases, Developer work units) and wait for the user to approve or adjust it.

1. For large changes, invoke the tech-lead agent and wait for plan approval.
2. Create a new feature branch (`git checkout -b feature/{{LINEAR_ISSUE_PREFIX}}-XX-<short-description>`) and switch to it before writing any code. Always include the Linear ticket number after `feature/`.
3. Write failing tests that describe the expected behaviour.
4. Implement the minimum code to make the tests pass.
5. Refactor if needed.
6. Run tests and linting — fix any failures before proceeding.
7. Update documentation if affected by the changes:
    - `CLAUDE.md` — architecture, conventions, or workflow changed
    - `@docs/PRODUCT_SPEC.md` — functionality added, removed, or changed
    - `@docs/ARCHITECTURE.md` — code structure or dependencies changed
    - `@docs/VERSIONING.md` — CI/CD or versioning process impacted
8. Commit all changes with a descriptive message.
9. Run a smoke test and wait for the user to confirm before proceeding.
10. Push to the remote.
11. Open a PR and request reviews in parallel (both agents are independent — launch them simultaneously):
    - If `.claude/agents/tech-lead.md` exists, invoke it for an architectural review: `Use the tech-lead agent to review PR #<number>`.
    - If `.claude/agents/code-reviewer.md` exists, invoke it for a runtime/launch/migration review: `Use the code-reviewer agent to review PR #<number>`.
    - If neither agent exists, request a review from the user directly.
12. Remind the user to compact the context after each commit to keep the conversation lean.
13. When the user approves the PR:
    - Invoke the `product-owner` agent: `Use the product-owner agent to close the approved PR's Linear issues, regenerate BACKLOG.md and CHANGELOG.md, and merge the PR`.
14. Clear the context after the PR with the changes is merged.
