---
name: ship
effort: RAPID
reasoning: TACTICAL
description: Post-merge housekeeping after a PR/MR is approved. Closes the linked PM issues, adds a CHANGELOG entry, regenerates BACKLOG.md, bumps the version, commits everything onto the feature branch, pushes, and merges. Invoke when the user approves a PR/MR, before merging.
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

### 5. Commit, push, and merge

Stage only the files changed above and commit onto the feature branch:

```bash
git add docs/CHANGELOG.md docs/BACKLOG.md <version-file>
git commit -m "chore: release {{ISSUE_PREFIX}}-XX, bump version to X.Y.Z"
git push
```

Then merge the PR/MR on your Git host:

| Host | Command |
|---|---|
| GitHub | `gh pr merge {number} --squash --delete-branch` |
| GitLab | `glab mr merge {iid} --squash --remove-source-branch` |
| Bitbucket | merge via Bitbucket REST API or UI |

### 6. Report back

Confirm: issue(s) closed, changelog updated, version bumped, PR/MR merged. Include the new version number and the PR/MR URL.
