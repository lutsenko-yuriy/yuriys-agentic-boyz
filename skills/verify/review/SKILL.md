---
name: review
effort: FOCUSED
reasoning: ARCHITECTURAL
output_style: CONCISE
description: Architectural review of a PR/MR. Checks for layer violations, dependency direction, module boundary breaches, naming/placement issues, and interface drift. Leaves inline comments prefixed with [review] and produces a structured summary. Invoke after `implement` opens a PR/MR, before human review, in parallel with `audit`.
---

The Git host is **{{GIT_HOST}}**. The issue identifier prefix is **{{ISSUE_PREFIX}}**.

This skill produces reviews, not code.

---

## Steps

### 1. Resolve the repository and PR/MR details

Get the repo slug and PR/MR metadata:

| Host | Command |
|---|---|
| GitHub | `git remote get-url origin` → extract `{owner}/{repo}`; then `gh pr view {number} --json headRefOid,files` |
| GitLab | `git remote get-url origin` → extract project path; then `glab mr view {iid}` |
| Bitbucket | `git remote get-url origin` → extract workspace/repo slug; use Bitbucket REST API |

### 2. Fetch the full diff

| Host | Command |
|---|---|
| GitHub | `gh pr diff {number}` |
| GitLab | `glab mr diff {iid}` |
| Bitbucket | `git diff origin/main...HEAD` or Bitbucket REST API |

### 3. Read changed source files

Read the full source of every changed file that is relevant to the architecture. Do not rely on the diff alone.

### 4. Check for architectural concerns

Evaluate each changed file against:

- **Layer violations** — wrong import direction between layers
- **Dependency direction** — new dependencies that point inward
- **Module / slice boundaries** — code reaching into another module's internals
- **Naming and placement** — files in the right directories per `docs/ARCHITECTURE.md`
- **Interface coverage** — interfaces updated when implementations change their contract
- **Architectural drift** — patterns inconsistent with the rest of the codebase without justification

Before flagging a finding, verify:
- Is the scenario already handled by a path not visible in the diff?
- Does an existing test cover this case?

Only report findings you can fully characterise.

### 5. Leave inline comments

For each finding tied to a specific file and line, post an inline comment. Prefix every comment body with `**[review]**`.

| Host | Command |
|---|---|
| GitHub | `gh api repos/{owner}/{repo}/pulls/{pr}/comments --method POST --field body="**[review]** <comment>" --field commit_id="<head sha>" --field path="<file>" --field line=<line> --field side="RIGHT"` |
| GitLab | `glab api projects/{id}/merge_requests/{iid}/notes --method POST -f body="**[review]** <comment>"` (inline: use `position` params for diff notes) |
| Bitbucket | `POST /2.0/repositories/{workspace}/{repo}/pullrequests/{id}/comments` with `inline.path` and `inline.to` |

For findings that span multiple files, post a general PR/MR comment without the `path` / `line` fields.

Post one comment per distinct finding. Do not batch unrelated issues.

### 6. Produce a structured summary

After posting all comments:

```
### Architectural review — PR/MR #<N>

#### 🔴 Must fix before merge
<finding: layer or boundary violation that would compound over time>

#### 🟡 Should fix
<finding: inconsistency or naming drift that makes the codebase harder to navigate>

#### ✅ Architecture looks good
<brief note on what was done correctly>
```

Omit a section if empty. Do not flag style issues — those belong to the `audit` skill.
