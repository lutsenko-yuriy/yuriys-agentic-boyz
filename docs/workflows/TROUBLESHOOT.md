# Troubleshooting Workflow

Use this workflow for reactive work: CI failures, regressions, infrastructure breakage, build system issues.
For new features, enhancements, and planned changes, use `docs/workflows/FEATURE.md` instead.

@skills/shared/decision-guidelines.md

## 1. Identify and reproduce

- Confirm the problem is real by checking CI logs or reproducing locally.
- Note the first failing commit or PR/MR if identifiable.
- State the problem in one sentence before going further.

## 2. Investigate

- Check recent changes: `git log --oneline -20`, recent PRs/MRs, recent dependency bumps.
- For third-party tool failures: read the changelog for breaking changes around the time the failure started.
- **Before writing off a failing test as "known flaky"**, re-run it in isolation at least once to confirm it's actually intermittent, not deterministic. A symptom that looks like known flakiness (e.g. a timeout) can be a real, consistent bug wearing the same clothes.
- Form a hypothesis before attempting any fix. **If a hypothesis is disproven by a live CI run, don't form a second one from code reading alone** — add targeted diagnostic instrumentation and validate against real data before the next attempt.
- **Same rule for a visual/timing bug** reported by the user: if a fix attempt doesn't resolve it, ask for concrete evidence of the actual runtime state (a screen recording, a trace, a log capture) instead of forming another hypothesis from code alone.

## 3. Open a tracking ticket

**Before attempting more than one fix**, open a ticket with:
- Problem description and first observed failure
- What has already been tried and why it failed
- Candidate solutions with a trade-off analysis

**When candidates include third-party CI actions or OSS dependencies**, include a health check for each in the trade-off table:

| Signal | How to fetch |
|---|---|
| License | `gh api repos/{owner}/{repo} --jq '.license.spdx_id'` |
| Open issues (count + nature) | `gh api "repos/{owner}/{repo}/issues?state=open&per_page=25"` |
| Last commit date | `gh api repos/{owner}/{repo} --jq '.pushed_at'` |
| Stars / forks | same API call |

Present this alongside the trade-off table, not only when asked.

## 4. Attempt fixes systematically

- One branch per attempt: `feature/{{ISSUE_PREFIX}}-XX-<short-description>`
- Record each failed attempt in the ticket description before moving on.
- Use `workflow_dispatch` or equivalent to test CI fixes without merging.
- If the fix loop looks like it will need multiple real CI dispatches to validate (e.g. CI-only environment flakiness), say so explicitly — at ticket start if apparent from the outset, or the moment it becomes apparent mid-ticket — so the user can choose to step away (e.g. overnight) instead of staying attached through every dispatch.

## 5. Ship

Once a fix works, follow `docs/workflows/FEATURE.md` steps 7–13 (CHANGELOG, version bump, PR/MR, review, debrief, merge via `/ship`).
