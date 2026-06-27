# PM Tool Mapping

Fill in this file when setting up the project. Skills reference this for all PM tool operations.
When porting to a different PM tool, replace this file — skill logic stays unchanged.

## Identity

| Setting | Value |
|---|---|
| Tool | `{{PM_TOOL}}` (e.g. Linear, Jira, GitHub Issues, GitLab) |
| Issue prefix | `{{ISSUE_PREFIX}}` (e.g. `APP`, `PROJ`, `HAB`) |

## Workspace IDs

| Setting | Value |
|---|---|
| Team / Board ID | `{{TEAM_ID}}` |
| Project / Space ID | `{{PROJECT_ID}}` |

## Operation mapping

| Operation | Linear | Jira | GitHub Issues | GitLab |
|---|---|---|---|---|
| Fetch issue | `mcp__linear__get_issue` | `GET /rest/api/3/issue/{key}` | `gh issue view {n}` | `glab issue view {n}` |
| List issues | `mcp__linear__list_issues` | `GET /search?jql=…` | `gh issue list` | `glab issue list` |
| Create issue | `mcp__linear__save_issue` (no `id`) | `POST /rest/api/3/issue` | `gh issue create` | `glab issue create` |
| Update issue | `mcp__linear__save_issue` (with `id`) | `PUT /rest/api/3/issue/{key}` | `gh issue edit {n}` | `glab issue update {n}` |
| Move issue to state | `mcp__linear__save_issue` with `state:` | `POST /issue/{key}/transitions` | label or close | label or close |
| List comments | `mcp__linear__list_comments` | `GET /issue/{key}/comment` | `gh issue comment list {n}` | `glab issue note list {n}` |
| Post comment | `mcp__linear__save_comment` | `POST /issue/{key}/comment` | `gh issue comment {n} --body` | `glab issue note create {n}` |
| Fetch milestone | `mcp__linear__get_milestone` | sprint/version API | `gh api milestones/{n}` | `glab api milestones/{n}` |
| List milestones | `mcp__linear__list_milestones` | sprint/version list API | `gh api milestones` | `glab api milestones` |
