---
name: implement
effort: FOCUSED
reasoning: TACTICAL
output_style: CONCISE
description: Implement a work unit from an approved plan. Given a PM issue ID, fetches the plan comment, follows strict TDD (red → green → refactor), creates the feature branch, runs tests and linting, commits with a style-only commit first, pushes, and opens a PR/MR. Does not merge — that is the `ship` skill's job.
---

The project management tool is **{{PM_TOOL}}**. The Git host is **{{GIT_HOST}}**. The issue identifier prefix is **{{ISSUE_PREFIX}}**.

---

## Setup (do this first, every time)

1. Read `CLAUDE.local.md` for local binary paths and environment settings.
2. Read `CLAUDE.md` and `docs/ARCHITECTURE.md` to orient yourself before touching any code.

---

## Workflow

### 1. Fetch the plan

Retrieve the issue details and find the implementation plan comment left by the `plan` skill:

| Tool | How |
|---|---|
| Linear | `mcp__linear__get_issue`, then `mcp__linear__list_comments` on the issue |
| Jira | `GET /rest/api/3/issue/{key}` and `GET /rest/api/3/issue/{key}/comment` |
| GitHub Issues | `gh issue view {number}` and `gh issue comment list {number}` |
| GitLab | `glab issue view {number}` and `glab issue note list {number}` |

**If no approved plan comment exists — stop.** Report back:

> "No approved plan found on {{ISSUE_PREFIX}}-XX. Invoke the `plan` skill to produce and approve a plan before implementation can begin."

### 2. Move issue to In Progress

Update the issue status to **In Progress** in the PM tool.

| Tool | How |
|---|---|
| Linear | `mcp__linear__save_issue` with `state: "In Progress"` |
| Jira | `POST /rest/api/3/issue/{key}/transitions` with the In Progress transition |
| GitHub Issues | `gh issue edit {number} --add-label "in-progress"` |
| GitLab | `glab issue update {number} --label "in-progress"` |

### 3. Create or switch to the feature branch

Branch naming: `feature/{{ISSUE_PREFIX}}-XX-<short-description>` (2–4 words, kebab-case).

- If already on the correct branch, continue.
- Otherwise: `git checkout -b feature/{{ISSUE_PREFIX}}-XX-<short-description>`

### 4. TDD cycle

**Red — write failing tests first.**

Write tests that describe the expected behaviour before writing any implementation. Run the test command (see `CLAUDE.md` → "Common Commands") to confirm they fail.

**Green — implement the minimum code to pass.**

Write only what is needed to make the failing tests pass. Follow `docs/ARCHITECTURE.md` for structure and `CLAUDE.md` for code style.

**Refactor — clean up without breaking tests.**

Remove duplication, improve naming, simplify logic. Re-run tests after every refactor step.

### 5. Schema / data migrations

If your implementation adds, removes, or renames storage structures (database tables, columns, storage keys, data format), write a migration before committing:

1. Bump the schema version.
2. Add an upgrade handler for each version step.
3. Write a migration test: open a store at the previous version, re-open with the new version, assert new structure exists and existing data is preserved.
4. Never apply destructive changes (dropping a column with user data) without explicit user approval — stop and ask first.

### 6. Validate

Run the test and lint commands from `CLAUDE.md` → "Common Commands". Fix every failure before proceeding.

### 7. Localisation

If the project uses localisation and user-visible strings were added, follow the localisation process defined in `CLAUDE.md`.

### 8. Request documentation updates

If your changes affect architecture or user-visible functionality, **do not update those docs yourself** — ask the orchestrator to invoke the appropriate skill and wait for confirmation:

- **`docs/ARCHITECTURE.md`** affected → ask orchestrator to invoke `plan` to update it.
- **`docs/PRODUCT_SPEC.md`** affected → ask orchestrator to invoke `summarize` to update it.

Both can be requested simultaneously. Only proceed after the orchestrator confirms those updates are committed.

Never update `docs/BACKLOG.md` or `docs/CHANGELOG.md` — those are owned by the `ship` skill.

### 9. Format

Apply the project's formatter in a **separate, formatting-only commit before the functional commit**:

```bash
# run formatter (see CLAUDE.md for the command)
# if any files changed:
git add <only changed files>
git commit -m "style: apply formatter ({{ISSUE_PREFIX}}-XX)"
```

If no files changed, skip this step. Never mix formatting and functional changes in the same commit.

### 10. Commit

Stage only the files you changed (never `git add -A` or `git add .`):

```bash
git commit -m "$(cat <<'EOF'
<type>: <short summary>

<optional body explaining why this change was needed>

{{AI_COMMIT_TRAILER}}
EOF
)"
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.

### 11. Push

```bash
git push -u origin <branch-name>
```

### 12. Open a PR/MR

| Host | Command |
|---|---|
| GitHub | `gh pr create --title "<type>: <summary>" --body "..."` |
| GitLab | `glab mr create --title "<type>: <summary>" --description "..."` |
| Bitbucket | `bb pr create` or use the Bitbucket REST API |

PR/MR body template:

```
## Summary
- <bullet points>

## {{PM_TOOL}}
Closes {{ISSUE_PREFIX}}-XX

## Test plan
- [ ] <what was tested>
- [ ] Tests pass
- [ ] Linting passes
- [ ] Smoke tested

{{AI_TOOL_CREDIT}}
```

### 13. Move issue to In Review

Update the issue status to **In Review**.

| Tool | How |
|---|---|
| Linear | `mcp__linear__save_issue` with `state: "In Review"` |
| Jira | Transition to In Review |
| GitHub Issues | `gh issue edit {number} --add-label "in-review"` |
| GitLab | `glab issue update {number} --label "in-review"` |

### 14. Post the PR/MR link to the issue

Add a comment on the issue with the PR/MR URL.

| Tool | How |
|---|---|
| Linear | `mcp__linear__save_comment` |
| Jira | `POST /rest/api/3/issue/{key}/comment` |
| GitHub Issues | `gh issue comment {number} --body "PR opened: <url>"` |
| GitLab | `glab issue note create {number} --message "MR opened: <url>"` |

### 15. Request reviews

Report back to the orchestrator:

> "PR/MR #<N> is open at <url>. Please invoke `review` and `audit` simultaneously."

### 16. Report back

Return: what was built, PR/MR number and URL, test results, any deviations from the plan and why.

---

## Constraints

- **TDD is non-negotiable.** Tests must be red before implementation starts.
- **No plan = no code.** Stop and escalate if the plan comment is missing.
- **Do not touch version files** — bumps require explicit user approval per `docs/VERSIONING.md`.
- **Do not merge** — that is the `ship` skill's responsibility.
- **Do not update `docs/ARCHITECTURE.md` or `docs/PRODUCT_SPEC.md` directly** — delegate as described in step 8.
- Fix all test and lint failures before opening the PR/MR. Never leave the build red.
