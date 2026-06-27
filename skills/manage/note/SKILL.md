---
name: note
effort: RAPID
reasoning: MECHANICAL
output_style: CONCISE
description: Capture a quick observation or decision into the project knowledge base mid-session. Infers the active ticket from session context (confirms before writing), appends a timestamped bullet to docs/knowledge/notes/{{ISSUE_PREFIX}}-XX.md, and creates the file if it does not yet exist.
---

@skills/shared/project-config.md

This skill writes one entry, then stops. It does not open a dialog.

---

## Steps

### 1. Resolve the ticket tag

**If the argument starts with `{{ISSUE_PREFIX}}-XX:` (explicit tag):** use that ticket ID. Strip the `{{ISSUE_PREFIX}}-XX:` prefix to get the note text.

**If no explicit tag:** check the current session context for an active ticket (e.g. a ticket currently In Progress, or one mentioned in the recent conversation).

- If a ticket is found: ask once — *"This note will be tagged to {{ISSUE_PREFIX}}-XX — correct?"* Wait for confirmation before writing.
  - If the user confirms: proceed with that ticket.
  - If the user corrects it (supplies a different ticket or label): use the corrected value.
- If no ticket is found: ask the user — *"Which ticket should this note be tagged to?"* Use the answer; do not guess.

One question maximum. Do not write until the ticket is resolved.

### 2. Resolve the note text

The note text is everything after the `{{ISSUE_PREFIX}}-XX:` prefix in the argument, or the full argument if no explicit tag was given.

If the argument is empty after stripping the tag (or no argument was given at all): ask — *"What's the note?"* — and use the answer.

### 3. Write the entry

Resolve the target file: `docs/knowledge/notes/{{ISSUE_PREFIX}}-XX.md` (using the ticket ID from step 1).

**If the file does not exist:** create it with this structure:

```markdown
# {{ISSUE_PREFIX}}-XX: <ticket title>

## Notes

## Debrief summary
```

**Append** a timestamped bullet at the end of the `## Notes` section (after all existing bullets, or as the first line if there are none yet):

```
- YYYY-MM-DD: <note text>
```

Use today's date in `YYYY-MM-DD` format.

### 4. Report back

One line: *"Noted in `docs/knowledge/notes/{{ISSUE_PREFIX}}-XX.md`."*

---

## Constraints

- Never write to `## Debrief summary` — that section belongs to `/debrief`.
- One question maximum across all steps. If both the ticket and the note text are unknown, ask for the ticket first; ask for the note text in the same response only if the ticket was explicit in the argument.
- Never modify production code, tests, or any file outside `docs/knowledge/notes/`.
