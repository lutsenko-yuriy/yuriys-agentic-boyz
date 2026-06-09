---
name: plan
effort: THOROUGH
reasoning: ARCHITECTURAL
output_style: DETAILED
description: Produce a structured implementation plan for a PM issue or milestone before any code is written. Fetches the issue, reads the codebase, breaks the work into implementation units, posts the plan as a PM comment, and waits for user approval. For large changes spanning multiple files, new domain entities, new dependencies, or architectural shifts.
---

The project management tool is **{{PM_TOOL}}**. The issue identifier prefix is **{{ISSUE_PREFIX}}**.

This skill produces plans, not code.

---

## Steps

### 1. Fetch the issue(s)

Retrieve the full details of each issue passed in (title, description, acceptance criteria, comments).

| Tool | How |
|---|---|
| Linear | `mcp__linear__get_issue` for each ID; if a milestone was named, `mcp__linear__get_milestone` then list issues filtered to it |
| Jira | `GET /rest/api/3/issue/{key}` |
| GitHub Issues | `gh issue view {number}` |
| GitLab | `glab issue view {number}` |

### 2. Read the codebase

Read `docs/ARCHITECTURE.md`, `docs/PRODUCT_SPEC.md`, and the source files most relevant to the work. Use search tools to locate existing models, repositories, view models, and UI files. Name real files and classes — do not invent hypothetical ones.

### 3. Produce the implementation plan

Use this format exactly. Omit a section entirely if it has no content.

@skills/design/plan/resources/plan-template.md

### 4. Post the plan as a PM comment

Post the full plan text as a comment on the primary issue so `implement` can reference it.

| Tool | How |
|---|---|
| Linear | `mcp__linear__save_comment` on the issue |
| Jira | `POST /rest/api/3/issue/{key}/comment` |
| GitHub Issues | `gh issue comment {number} --body "..."` |
| GitLab | `glab issue note create {number} --message "..."` |

### 5. Present and wait

Show the plan to the user and wait for approval or adjustments. Do not proceed until the user explicitly approves.

### 6. Update ARCHITECTURE.md (after approval)

If the plan introduces new layers, directories, classes, or dependencies not already in `docs/ARCHITECTURE.md`, update that file now. Keep the existing structure — add to it, do not rewrite it.

---

## Constraints

- Do not write application code.
- Keep plans concrete: reference real files and classes from the current codebase.
- Never modify `CLAUDE.md` — that is the orchestrator's file.
