# Project Knowledge Base

A local Markdown vault for decisions, learnings, and retrospectives — committed to the repo so the agent and the user share the same history across sessions.

## Structure

```
docs/knowledge/
├── README.md          # this file
└── notes/
    └── {{ISSUE_PREFIX}}-XX.md      # one file per ticket; created on first /note or /debrief use
```

## Per-ticket file format

```markdown
# {{ISSUE_PREFIX}}-XX: <ticket title>

## Notes
- YYYY-MM-DD: <free-form observation captured mid-session>

## Debrief summary
### YYYY-MM-DD
<structured retrospective written by /debrief after the ticket closes>
```

## How entries are written

| Command | Writes to |
|---|---|
| `/note [{{ISSUE_PREFIX}}-XX:] <text>` | Appends a timestamped bullet to `## Notes` |
| `/debrief {{ISSUE_PREFIX}}-XX` | Appends a dated block to `## Debrief summary` |

On first use for a ticket, the file is created with both section headers before the entry is appended.

## How to query

- All notes for a ticket: `grep -r "{{ISSUE_PREFIX}}-XX" docs/knowledge/notes/`
- Recent decisions: open `docs/knowledge/notes/{{ISSUE_PREFIX}}-XX.md` directly
- The agent reads the relevant file at the start of `/debrief` and can be asked to read any file on demand
