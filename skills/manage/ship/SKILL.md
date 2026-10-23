---
name: ship
effort: RAPID
reasoning: TACTICAL
output_style: CONCISE
description: Post-merge housekeeping after a PR/MR is approved. Closes the linked PM issues, adds a marked CHANGELOG line under [Unreleased], regenerates BACKLOG.md, proposes PRODUCT_SPEC.md and GLOSSARY.md updates for approval, commits everything onto the feature branch, pushes, and merges. Invoke when the user approves a PR/MR, before merging.
---

The project management tool is **{{PM_TOOL}}**. The issue identifier prefix is **{{ISSUE_PREFIX}}**.

@skills/shared/git-cli-safety.md

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

### 2. Add a CHANGELOG line

Append one line after the last `- ` line of the `## [Unreleased]` section of `docs/CHANGELOG.md`: the real heading at the start of a line, outside any HTML comment. The indented `## [Unreleased]` in the footer comment is only a format example; never write there. If the real heading is absent, create it right after the intro's first `---` rule. The grammar and tags are in `skills/manage/ship/resources/changelog-tags.md`:

```markdown
## [Unreleased]
- {{ISSUE_PREFIX}}-XX: <one-line summary of what changed> (PR #N) [user] MINOR flags: name1, name2
```

- **Tag:** the classification tag(s) for this PR/MR.
- **Mark** (`[user]`/`[app]` lines only): propose `MAJOR`, `MINOR` or `PATCH` from the issue and the diff, per `docs/VERSIONING.md` (breaking change, new feature, fix). Ask the user to confirm or change it before writing.
- **Flags:** only when `skill_router.toml` `[tools].feature_flags` is not `none` and the feature has flags: the names of the flags that switch it on and off, after the mark.

Never write a numbered `## [X.Y.Z]` heading or bump the version file: `/prepare-release` does both when a release is cut.

### 3. Regenerate BACKLOG.md

Open `docs/BACKLOG.md` and make two edits:

1. **In Progress section** — replace the in-progress bullet with `_(nothing in progress)_`.
2. **Milestone section** — remove the completed ticket(s) from the remaining-work list for their milestone.

Do not rewrite the rest of the file — the milestone sections are the source of truth from the PM tool.

### 4. Update PRODUCT_SPEC.md and GLOSSARY.md

Skip this step if the new CHANGELOG line (added in step 2) has no `[user]` tag — those PRs introduce no observable user-facing behaviour change. For all other PRs (`[user]` entries), proceed as follows:

1. Fetch the PR/MR diff (GitHub: `gh pr diff <number>` · GitLab: `glab mr diff <iid>`).
2. Re-read the ticket description (already fetched in step 1).
3. Determine what changed or was added:
   - **Product spec** (`docs/PRODUCT_SPEC.md`) — identify any new or modified user-facing behaviour. Propose a minimal, precise addition or edit to the relevant section (append a new bullet or update an existing one; never rewrite unrelated content).
   - **Glossary** (`docs/GLOSSARY.md`) — identify any new canonical domain terms introduced by the feature. For each, propose a new entry with a definition.
4. Present the proposed changes to the user **before writing anything**. Show the exact text to be added or replaced. Wait for explicit approval or revision instructions.
5. Apply only the approved changes.

If no changes are needed for a file, skip it. If the user declines all changes, skip to step 5.

### 5. Commit, push, and merge

Lint the CHANGELOG and fix any finding on the new line before committing:

```bash
python3 scripts/changelog/changelog.py lint docs/CHANGELOG.md
```

If the output has a `notice` (the CHANGELOG has no `<!-- changelog-format: yab-1 -->` line, so it was not linted), tell the user and point to the Release flow in `docs/VERSIONING.md` for opting in; do not add the marker without their go.

Stage only the files changed above and commit onto the feature branch:

```bash
git add docs/CHANGELOG.md docs/BACKLOG.md
# add only if modified in step 4:
git add docs/PRODUCT_SPEC.md docs/GLOSSARY.md
git commit -m "chore: CHANGELOG for {{ISSUE_PREFIX}}-XX"
git push
```

Then merge the PR/MR on your Git host. Prefer a merge commit; use another method only when the repository does not allow it.

| Host | Command |
|---|---|
| GitHub | Check which methods the repository allows with `gh repo view --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed`, then use the first allowed one: `gh pr merge {number} --merge --delete-branch`, else `gh pr merge {number} --squash --delete-branch`, else `gh pr merge {number} --rebase --delete-branch`. |
| GitLab | `glab mr merge {iid} --remove-source-branch`: it follows the GitLab project's own merge method setting. |
| Bitbucket | merge via Bitbucket REST API or UI |

The merge method does not affect releases: `/prepare-release` finds the release commit with a first-parent lookup, which works with every merge method.

### 6. Report back

Confirm: issue(s) closed, CHANGELOG line added (quote it), docs updated (list which files changed), PR/MR merged. Include the PR/MR URL.

After reporting, propose: *"Want to run `/debrief {{ISSUE_PREFIX}}-XX` to capture what you learned from this ticket?"* (optional — do not block on it)
