---
name: prepare-release
effort: FOCUSED
reasoning: TACTICAL
needs_session_tools: true
output_style: CONCISE
description: Cut a release from the CHANGELOG's [Unreleased] lines. Shows the [user]/[app] lines for selection, drafts plain-language release notes, proposes the next version from the highest semver mark, and after the user's "go" makes the release commit (version gates, version bump, release heading), tags vX.Y.Z, starts the release job if one is recorded and switches the selected flags on. On a protected default branch it opens a release PR/MR and stops until the user has merged it.
---

@skills/shared/project-config.md

@skills/shared/git-cli-safety.md

The Git host is **{{GIT_HOST}}**. Run this skill **inline in the main session** (no subagent): it is a dialog and waits for the user's answers.

Inputs: the user's selection and their "go". Nothing is written, committed, tagged or published before "go". Release flow and terms: `docs/VERSIONING.md` (Release flow). Config: `skill_router.toml` `[project].version_file`/`version_field`, `[release].job`, `[release].version_gates` and `[tools].feature_flags`, read as described in `skills/shared/project-config.md` (Release, Tools).

`changelog.py` below is `python3 scripts/changelog/changelog.py`. Every subcommand prints JSON (except `notes`) and exits 1 on a refusal: show its `error` to the user and stop or fix as the step says. If any output carries a `notice` (no format marker), relay it once.

---

## 1. Preconditions

1. Find the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`, minus `origin/`). Run `git fetch origin --tags`. The working tree must be clean and on the default branch, level with `origin/<default>`. Otherwise stop and say what to fix; never stash or reset the user's work.
2. `changelog.py lint docs/CHANGELOG.md`. Findings: stop and list them.

## 2. Previous version

- `changelog.py latest docs/CHANGELOG.md` gives the latest released heading.
- `git tag --list 'v*' --sort=-v:refname` gives the latest `vX.Y.Z` tag (first line).
- If both exist and disagree, stop and ask the user which is right; do not guess.
- With no release heading and no tag, the base is the version-file value (`[project].version_file`, field `[project].version_field`), or `0.0.0` without one.

## 3. Lines to release

`changelog.py unreleased docs/CHANGELOG.md` returns the `[user]`/`[app]` lines (`line`, `text`, `tags`, `mark`, `flags`) and the count of other lines.

- No app lines: say there is nothing to release and stop.
- A line without a mark (an adopter's unmigrated line): show `?` in the table and ask the user for `MAJOR`, `MINOR` or `PATCH`. Do not fail. The supplied marks are passed as `--mark <line>=<MARK>` to `propose` (step 5) and `cut` (step 6), which writes them to the lines.

Show one table and ask the user to accept all, reject all, or deselect lines or flags:

| # | Line | Tag | Mark | Flags |
|---|---|---|---|---|

Selection rules:

- The selection unit for a flagged line is the flag. A line goes in only if every flag it names is selected.
- Lines without flags go in unless the user deselects them.
- Non-app lines (`[meta]`, `[ci]`, `[test]`, `[wip]`) are not shown. They move with the release, because they are in the tagged commit.
- Reject all: say nothing was changed and stop.

The deselected lines (by their `line` number) are the `--keep` list for every step below.

## 4. Release notes

Draft one bullet per selected `[user]` line, then check each against `skills/manage/prepare-release/resources/notes-checklist.md` and rewrite any that fail. `[app]` lines produce no bullets. Zero bullets is a valid result: say "no release notes (no user-visible changes)".

## 5. Summary and "go"

Propose the version with `changelog.py propose docs/CHANGELOG.md --current <previous> --keep <deselected line numbers> --mark <line>=<MARK>…` (one `--mark` value per mark the user supplied in step 3). The user may override the version with any `X.Y.Z` greater than the previous one.

Show one summary screen:

1. **Version:** `<previous>` → `X.Y.Z` (from the highest mark), tag `vX.Y.Z`.
2. **Release:** the selected lines. **Deferred:** the deselected lines, which stay in `[Unreleased]`.
3. **Release notes:** the drafted bullets.
4. **Version file:** `[project].version_file`, field `[project].version_field`, set to `X.Y.Z`; the build number is left alone. Without a version file, say none is bumped.
5. **Version gates** (only when selected lines name flags):
   - `[release].version_gates` names a file and symbol: list each selected flag with `X.Y.Z` as its gate entry.
   - `[release].version_gates` is `none`: warn that switching these flags on also enables the feature on older builds that do not contain it.
   - `[release].version_gates` is not recorded: ask for the gate location, or for an explicit "proceed without gates" with the same warning. Do not continue without one of the two answers.
6. **Release job:** the `[release].job` command with `{version}` and `{tag}` substituted. When it is `none` or not recorded: "publishing is up to you after the tag".
7. **Flags to switch on:** the selected flags, and how (step 9).
8. **Target:** push the release commit to `<default>`. If the push is rejected (protected branch), a `release/vX.Y.Z` PR/MR is opened instead and the skill waits for you to merge it.

Ask: say "go" to release, or change anything above. Re-show the summary after every change. Only an explicit "go" continues.

## 6. Release commit

1. Write the release-note bullets to a temp file (empty for zero bullets), then run
   `changelog.py cut docs/CHANGELOG.md X.Y.Z --keep <deselected line numbers> --mark <line>=<MARK>… --notes-file <temp file>`
   with the line numbers from step 3 and the same `--mark` values as step 5; it writes the supplied marks to their lines.
2. `changelog.py lint docs/CHANGELOG.md` must pass.
3. Set `[project].version_field` in `[project].version_file` to `X.Y.Z`. Keep the build number if the field has one.
4. Version gates: for each selected flag, add `X.Y.Z` as its gate in the symbol named by `[release].version_gates`, in the form the existing entries use. Skip when it is `none` or the user chose "proceed without gates".
5. Stage only these files and commit with `git commit -F <file>`, message `chore: release vX.Y.Z`.

## 7. Push

`git push origin <default>`.

**Rejected (protected branch):**

1. `git switch -c release/vX.Y.Z`, then `git push -u origin release/vX.Y.Z`.
2. Return the default branch to `origin/<default>`: the release commit now lives on the release branch, so this drops nothing.
3. Open a PR/MR from `release/vX.Y.Z` titled `chore: release vX.Y.Z`, with the summary as its body (GitHub: `gh pr create --body-file <file>`; GitLab: `glab mr create`). Open its URL in the browser.
4. **Stop.** Never merge it yourself: the branch's protection, review rules and merge method apply. Ask the user to merge it and to say "merged".
5. After "merged": `git fetch origin --tags`, `git switch <default>`, `git pull --ff-only`. The release commit is the first-parent commit that added the heading: `git log --first-parent -1 --format=%H -S'## [X.Y.Z]' origin/<default> -- docs/CHANGELOG.md`. Check that `changelog.py notes docs/CHANGELOG.md X.Y.Z` succeeds there. If nothing is found, stop and ask.

## 8. Tag and release job

1. `git tag -a vX.Y.Z -m "vX.Y.Z" <release commit>`, then `git push origin vX.Y.Z`. The tag is always on the commit that contains the release heading.
2. `[release].job` is a command: run it with `{version}` → `X.Y.Z` and `{tag}` → `vX.Y.Z`, and report its output (run URL if it prints one). If it fails, report the error; the tag stays, and the user can rerun the command.
3. `[release].job` is `none` or not recorded: say "Tagged vX.Y.Z; publishing is up to you." The job reads the release notes with `python3 scripts/changelog/changelog.py notes docs/CHANGELOG.md X.Y.Z` from the tagged commit.

## 9. Switch flags on

Only when selected lines name flags and `[tools].feature_flags` is not `none`.

Switch flags on yourself only after the release job succeeded: the step 8.2 command exited 0 and ran the release to the end, or, when it only starts a run (e.g. a workflow dispatch), the run finished successfully (watched to the end, or confirmed by the user). A flag switched on earlier would enable the feature before the build carrying it is out.

- Job succeeded and this session has an integration for that tool (an MCP server, or an authenticated CLI): switch each selected flag on through it, confirming each flag with the user first.
- Job succeeded, no integration: give the flags as a manual step ("switch these on in <tool>") and wait for "done".
- Job failed, still running unconfirmed, or `[release].job` is `none` or not recorded: switch nothing. Give the flags as a manual step: "switch these on in <tool> once vX.Y.Z is published", and wait for "done".

## 10. Report

Version and tag, release commit (or release PR/MR URL), lines released and deferred, release notes, gates added, job result, flags switched on or handed over.
