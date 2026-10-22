Every merged PR/MR adds one line under `## [Unreleased]`:

```
- <ID>: <summary> (PR #N) [tag]… <MARK> flags: <name>, <name>
```

The mark and `flags:` are written without brackets, and are present only as the rules below require.

- **Tags** are the trailing `[…]` group. Brackets earlier in the summary (e.g. `[tools]`) are plain text.
- **Mark**: `MAJOR`, `MINOR` or `PATCH`, the semver step this change needs. Required on `[user]`/`[app]` lines, forbidden on all others.
- **Flags**: only after a mark, and only when `skill_router.toml` `[tools].feature_flags` is not `none` and the feature has flags. Names the flags that switch the feature on and off; names match `[A-Za-z0-9_.-]+`, comma-separated.
- `(PR #N)` is optional.
- **One line per entry, no wrapping.** In `[Unreleased]`, lint accepts only entry lines, `### ` subheadings, blank lines, `---` and HTML comments; a continuation line or prose note is a finding.

Examples:

```
- #12: Reminders can repeat weekly (PR #13) [user] MINOR flags: weekly_reminders
- #14: Faster sync on start-up (PR #15) [app] PATCH
- #16 WU1: reminder storage (PR #17) [wip]
- #18: /plan asks for test strategy (PR #19) [meta]
```

| Tag | When to use | Selected by `/prepare-release`? | Appears in release notes? |
|---|---|---|---|
| `[user]` | User-visible product change | Yes | Yes, rewritten in plain language |
| `[app]` | Code change, not user-visible | Yes | No |
| `[test]` | Test-only changes — no production code | No (moves with the release) | No |
| `[meta]` | Skills / agent / workflow change | No (moves with the release) | No |
| `[ci]` | CI/CD process change | No (moves with the release) | No |
| `[wip]` | Intermediate WU of a multi-WU ticket (`docs/workflows/MULTI_WU.md`) | No (moves with the release) | No |
| `[non-user]` | Supplementary tag within a classified line | — | No |

Rules:
- Every line must carry at least one of: `[user]`, `[app]`, `[test]`, `[meta]`, `[ci]`, `[wip]`.
- `[non-user]` is supplementary only — it does **not** satisfy the classification requirement on its own.
- `[user]` summaries must be readable by end users with no technical background: no class names, file paths, internal terms, or jargon.
- Numbered `## [X.Y.Z] — YYYY-MM-DD` sections are written by `/prepare-release`, never by hand or by `/ship`; only their heading format is linted, and older headings are accepted too: `-` or `–` before the date, no date, `??` date parts, `X.Y` or pre-release versions (`1.0.0-beta.1`).
- Check the file with `python3 scripts/changelog/changelog.py lint docs/CHANGELOG.md` (CI runs it too). It lints only a CHANGELOG containing the line `<!-- changelog-format: yab-1 -->`; without it, it prints a notice and passes (`docs/VERSIONING.md`, Release flow).
- The tag list may grow; each new tag must declare whether `/prepare-release` selects it and whether it appears in release notes, and be added to `scripts/changelog/changelog.py`.
