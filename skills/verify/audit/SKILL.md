---
name: audit
effort: THOROUGH
reasoning: TACTICAL
description: Runtime and migration review of a PR/MR. Checks for launch-time failures, migration issues, platform-specific risks, state consistency problems, and business logic edge cases. Leaves inline comments prefixed with [audit] and produces a structured summary. Invoke after `implement` opens a PR/MR, in parallel with `review`.
---

The Git host is **{{GIT_HOST}}**. The tech stack is **{{STACK}}**.

---

## What to look for

1. **Launch / startup failures** — anything that could crash or hang the app on cold start:
   - Singletons or providers that throw during initialisation
   - Missing or misconfigured platform/environment configuration
   - Assets or resources referenced in code but not registered
   - Dependencies expected to be injected but not overridden

2. **Migration issues** — anything that could break users upgrading from a previous version:
   - Database schema changes without a migration path (new tables, renamed/dropped columns)
   - Persisted data format changes (renamed enum values, new required fields in a stored model)
   - Storage keys that changed meaning or type
   - Scheduled task or notification identifiers that may conflict with older registrations

3. **Platform or environment-specific risks**:
   - Permission or capability differences between platforms
   - Background execution limits
   - OS or runtime version compatibility
   - Missing platform configuration (manifests, entitlements, config files)

4. **State and data consistency risks**:
   - Async operations that are fire-and-forget with no error handling
   - Repository or service methods that can partially succeed
   - Race conditions between concurrent reads and writes

5. **Edge cases in business logic**:
   - Off-by-one errors in date/range boundaries (inclusive vs exclusive ends)
   - Timezone and DST handling in scheduled values
   - Numeric overflow or precision issues

---

## How to review

### 1. Fetch the PR/MR diff and file list

| Host | Command |
|---|---|
| GitHub | `gh pr diff {number}` and `gh pr view {number} --json files` |
| GitLab | `glab mr diff {iid}` and `glab mr view {iid}` |
| Bitbucket | `git diff origin/main...HEAD` or Bitbucket REST API |

### 2. Read changed source files

Read the full source of any changed domain, data, or integration files. Do not rely on the diff alone.

### 3. Check configuration files

Look for related changes in manifests, lock files, env files, platform config.

### 4. Cross-reference intent

Read `docs/PRODUCT_SPEC.md` and `CLAUDE.md` to understand the intended behaviour and check against it.

### 5. Reason through each potential finding

Before reporting any finding, answer all four questions:
- What is the **exact sequence of events** that triggers the problem?
- Can the **existing code** handle this case through a path not visible in the diff?
- Is the scenario **already covered by a test**?
- What is the **worst-case outcome** — crash, data loss, silent wrong result?

Only report a finding if you can answer all four. A vague trigger scenario is not actionable — discard it.

---

## Leaving comments

Resolve the repo slug: `git remote get-url origin`.

For every finding tied to a specific file and line, post an **inline comment**. Prefix every comment body with `**[audit]**`.

| Host | Command |
|---|---|
| GitHub | `gh api repos/{owner}/{repo}/pulls/{pr}/comments --method POST --field body="**[audit]** <comment>" --field commit_id="<head sha>" --field path="<file>" --field line=<line> --field side="RIGHT"` |
| GitLab | `glab api projects/{id}/merge_requests/{iid}/notes --method POST -f body="**[audit]** <comment>"` (use `position` params for inline diff notes) |
| Bitbucket | `POST /2.0/repositories/{workspace}/{repo}/pullrequests/{id}/comments` with `inline.path` and `inline.to` |

For findings that span multiple files or cannot be tied to a specific line, post a general PR/MR comment without `path` / `line` fields.

Post one comment per distinct finding. Do not batch unrelated issues — each comment must be self-contained and actionable.

---

## Output format

After posting all comments, produce a structured summary. Omit a section entirely if there are no findings.

### 🔴 Critical — will likely break in production
Issues that would cause crashes, data loss, or silent failures for real users.

### 🟡 Warning — may break under specific conditions
Issues that require a particular state, OS version, or user action to trigger.

### 🟢 Suggestions — low risk, worth considering
Minor improvements to robustness or defensive coding that are not urgent.

### ✅ Looks good
A brief note on what was done well or poses no migration/launch risk.

Be precise: cite the file name, line range, and the exact scenario. Do not flag style issues or things already covered by existing tests unless the test itself is incorrect.
