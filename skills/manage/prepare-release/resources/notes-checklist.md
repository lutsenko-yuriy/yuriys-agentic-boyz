# Release-note bullet checklist

Release notes are read by end users as "What's New". Only `[user]` lines produce bullets; zero bullets is a valid result. Every drafted bullet must pass all items below before it is shown. A bullet that fails one is rewritten, not shown with a caveat.

1. **Understandable:** would a user with no background in software understand the sentence on its own?
2. **Cared about:** would they notice or care, or is the change invisible to them?
3. **No jargon:** no class names, file paths, flag or config key names, ticket or PR numbers, work-unit markers, or engineering terms ("refactor", "migration", "parameter", "flag", "state", "schema", "endpoint").
4. **Plain language:** reads like something a friend would say, not an engineer's or a product manager's changelog.
5. **Right altitude:** describes what changed for the user, not the mechanism behind it.
6. **Currently true:** describes what the user gets in this release, not an intermediate state a later change replaced.
7. **No promotion or calls to action:** states what changed; does not sell it or ask the user to do anything. App stores reject promotional release notes.

Drift to reject:

- Too technical: "Fixed off-by-one in `history_page_size`" → "The history list shows the right number of entries"
- Too designer-y: "Improved the UX of the bottom-sheet interaction" → "The list is easier to open and close"
- Too detailed: "Unified the term across fr/de/ru string files" → "Clearer wording in French, German and Russian"
- Too product-manager-y: "Introduced the confirmation variant for experiment 3" → "A new way to confirm before you save"
- Too promotional: "Check out our exciting new reminders — try them today!" → "You can now set weekly reminders."
