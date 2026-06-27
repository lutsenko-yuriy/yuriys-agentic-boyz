---
name: ship
effort: RAPID
reasoning: TACTICAL
output_style: CONCISE
description: Post-merge housekeeping after a PR/MR is approved. Closes the linked PM issues, adds a CHANGELOG entry, regenerates BACKLOG.md, bumps the version, proposes PRODUCT_SPEC.md and GLOSSARY.md updates for approval, commits everything onto the feature branch, pushes, and merges. Invoke when the user approves a PR/MR, before merging.
---

The project management tool is **{{PM_TOOL}}**. The issue identifier prefix is **{{ISSUE_PREFIX}}**.

---

## Steps

Run all steps in order. Each step must succeed before moving to the next.

### 1. Close the linked issue(s)

Move each issue linked to the PR/MR to **Done** (or the equivalent closed state) in the PM tool.

| Tool | How |
|---|---|
| Linear | `mcp__linear__save_issue` with `state: "Done"` |
| Jira | `POST /rest/api/3/issue/{key}/transitions` with the Done transition |
| GitHub Issues | `gh issue close {number}` |
| GitLab | `glab issue close {number}` |

### 2. Add a CHANGELOG entry

Open `docs/CHANGELOG.md` and prepend a new entry at the top:

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added / Changed / Fixed
- {{ISSUE_PREFIX}}-XX: <one-line summary of what changed>
```

Follow semantic versioning (`docs/VERSIONING.md`): patch for bug fixes, minor for new features, major for breaking changes.

### 3. Regenerate BACKLOG.md

Open `docs/BACKLOG.md` and make two edits:

1. **In Progress section** — replace the in-progress bullet with `_(nothing in progress)_`.
2. **Milestone section** — remove the completed ticket(s) from the remaining-work list for their milestone.

Do not rewrite the rest of the file — the milestone sections are the source of truth from the PM tool.

### 4. Bump the version

Find the project's version file (check `CLAUDE.md` → "Common Commands" for the stack-specific location, e.g. `pubspec.yaml`, `package.json`, `build.gradle`). Update the version string to match the new `[X.Y.Z]` entry added in step 2.

Do not touch the build number — CI manages it.

### 5. Update PRODUCT_SPEC.md and GLOSSARY.md

Skip this step if the new CHANGELOG entry (added in step 2) contains only `[meta]`, `[ci]`, or `[app]` tags — those PRs introduce no observable user-facing behaviour change. For all other PRs (`[user]` entries), proceed as follows:

1. Fetch the PR/MR diff (GitHub: `gh pr diff <number>` · GitLab: `glab mr diff <iid>`).
2. Re-read the ticket description (already fetched in step 1).
3. Determine what changed or was added:
   - **Product spec** (`docs/PRODUCT_SPEC.md`) — identify any new or modified user-facing behaviour. Propose a minimal, precise addition or edit to the relevant section (append a new bullet or update an existing one; never rewrite unrelated content).
   - **Glossary** (`docs/GLOSSARY.md`) — identify any new canonical domain terms introduced by the feature. For each, propose a new entry with a definition.
4. Present the proposed changes to the user **before writing anything**. Show the exact text to be added or replaced. Wait for explicit approval or revision instructions.
5. Apply only the approved changes.

If no changes are needed for a file, skip it. If the user declines all changes, skip to step 6.

### 6. Commit, push, and merge

Stage only the files changed above and commit onto the feature branch:

```bash
git add docs/CHANGELOG.md docs/BACKLOG.md <version-file>
# add only if modified in step 5:
git add docs/PRODUCT_SPEC.md docs/GLOSSARY.md
git commit -m "chore: release {{ISSUE_PREFIX}}-XX, bump version to X.Y.Z"
git push
```

Then merge the PR/MR on your Git host:

| Host | Command |
|---|---|
| GitHub | `gh pr merge {number} --squash --delete-branch` |
| GitLab | `glab mr merge {iid} --squash --remove-source-branch` |
| Bitbucket | merge via Bitbucket REST API or UI |

### 7. Report back

Confirm: issue(s) closed, changelog updated, version bumped, docs updated (list which files changed), PR/MR merged. Include the new version number and the PR/MR URL.

After reporting, propose: *"Want to run `/debrief {{ISSUE_PREFIX}}-XX` to capture what you learned from this ticket?"* (optional — do not block on it)
