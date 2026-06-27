---
name: summarize
effort: RAPID
reasoning: MECHANICAL
output_style: CONCISE
description: Present the current backlog at session start. Fetches open issues from the PM tool, shows the active milestone and completion percentage, groups work by label, and asks "What goes into the next release?" Invoke at the start of every session before any work begins.
---

The project management tool is **{{PM_TOOL}}**. The issue identifier prefix is **{{ISSUE_PREFIX}}** (e.g. `{{ISSUE_PREFIX}}-12`).

---

## Steps

### 1. Fetch open issues

List all open issues from the PM tool and group them by label:

- **Issues** — label `Bug` or `Tech Debt` — known problems already in the codebase
- **Remaining work** — label `Feature` or `Improvement` — planned work not yet started

| Tool | Command / API |
|---|---|
| Linear | `mcp__linear__list_issues` |
| Jira | `GET /rest/api/3/search?jql=project=KEY AND resolution=Unresolved` |
| GitHub Issues | `gh issue list --state open` |
| GitLab | `glab issue list --state opened` |

### 2. Fetch the active milestone

Get the current milestone (sprint, version, or release) and its completion percentage.

| Tool | Command / API |
|---|---|
| Linear | `mcp__linear__list_milestones` |
| Jira | Check the active sprint or fix version via the board API |
| GitHub | `gh api repos/{owner}/{repo}/milestones` |
| GitLab | `glab api projects/{id}/milestones` |

### 3. Produce the backlog summary

```
## Backlog — {{PROJECT_NAME}}

### Active milestone: <name> (<X>% complete)

### Issues (bugs & tech debt)
- {{ISSUE_PREFIX}}-XX: <title> — <one-line description>

### Remaining work
- {{ISSUE_PREFIX}}-XX: <title> — <one-line description>

### Recently completed
- <version>: <summary of what shipped>
```

### 4. Ask and wait

End with: **"What goes into the next release? Pick an existing ticket or describe something new."** — do not proceed until the user answers.

If the user wants to describe something new (says "something new", "new idea", "new feature", or otherwise indicates they want to start from scratch rather than pick an existing ticket), invoke the `brief` skill before any planning begins:

```
Invoke the brief skill
```

Do not jump to `plan` or `implement` for a new idea — always go through `brief` first so the idea is validated and a ticket is created.
