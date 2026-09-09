# Feature Workflow

Use this workflow for new features, enhancements, and planned changes.
For bugs, CI failures, regressions, or infrastructure breakage, use `docs/workflows/TROUBLESHOOT.md` instead.
For research-only tickets (no code change, just an investigation and a decision), use `docs/workflows/RESEARCH.md`.

Follow TDD: write or update tests **before** implementing the feature or fix. Red → Green → Refactor.

@skills/shared/decision-guidelines.md

**Ticket states and parallelism rules:**
- **Brief** → pre-implementation scoping (`/brief`, `/analyze`, `/plan`, `/draft-scenarios` gates from step 1 below) — used when this scoping genuinely spans multiple sessions/days, so it's visible separately from Backlog rather than looking untouched. Skip it for tickets that go straight into a single session's In Progress.
- **In Progress** → active development; only one ticket may be In Progress at a time (Brief does not count against this limit).
- **In Review** → PR/MR is open; code review is happening.
- **In QA / testing** → change is merged; automated and/or human verification is happening on the target environment. A new ticket **may** be picked up while another is In this state.
- **Done** → verification has signed off; the user moves the ticket to Done manually.

Before picking up any new ticket, check the PM tool to confirm no other ticket is In Progress.

## Trivial changes

A ticket is **trivial** when the change is content-only — the kind of edit that would
need nothing from us if this content lived in a CMS instead of the repo (a copy/string
tweak, an asset swap, a single literal value). No logic, no new/changed screen,
no architecture surface. Tag it `[trivial]` and take the short path instead of the full
workflow above:

1. Ticket created (via `/brief` or directly).
2. Change made directly on a feature branch — skip `analyze`/`plan`/`draft-scenarios`,
   same as any change with no user-facing flow.
3. PR/MR opened.
4. `/debrief` — skip the review loop (step 10) entirely; a trivial diff doesn't carry
   architectural or runtime risk worth two review passes.
5. Merge via `/ship`.

If a change *looks* small but touches logic, a new screen, or anything with runtime
behaviour beyond a literal value, it is not trivial — use the full workflow instead.

## Steps

1. **Planning & setup gates** — work through in order; skip any that don't apply. If this scoping is expected to span multiple sessions/days, move the ticket to **Brief** first and back to Backlog/Todo once it's done, before step 1.5 moves it to In Progress:
   1. **Sharpen the spec.** If the ticket lacks a clear spec (no explicit description of behaviour, interaction, or layout), or predates the `/brief` skill: run `/brief` first, before anything else below.
   2. **Analytics planning.** For features with user-visible screens or interactions: invoke `analyze` and wait for approval.
      ```
      Invoke the analyze skill for {{ISSUE_PREFIX}}-XX: <issue title>
      ```
      Identifies trackable moments, proposes events, flags PII concerns. Pure infrastructure or CI changes with no user-facing screens skip this gate.
   3. **Implementation plan.** For large changes (spanning multiple files, introducing new domain entities, new dependencies, or architectural shifts): invoke `plan` and wait for approval, before writing any code.
      ```
      Invoke the plan skill for {{ISSUE_PREFIX}}-XX: <issue title>
      ```
      Produces a structured plan (dependencies, models, UI changes, test strategy, ordered phases, work units).
   4. **Feature toggle.** For features introducing new user-facing behaviour: consider a remote-config-style kill-switch (default on) so the feature can be disabled without a release if a critical regression surfaces after shipping. If added, document it before writing any code.
   5. **Create the feature branch** from the latest default branch, before writing any code. Always include the ticket number after `feature/`:
      ```
      git fetch origin
      git checkout -b feature/{{ISSUE_PREFIX}}-XX-<short-description> origin/main
      ```
      If the branch already exists, rebase it onto `origin/main` first so the PR/MR diff contains only the new work. **Before merging**, rebase onto `origin/main` again so the branch is current and the merge lands cleanly.
   6. **Draft scenarios.** For every ticket with user-facing flows: invoke `draft-scenarios` and wait for approval.
      ```
      Invoke the draft-scenarios skill for {{ISSUE_PREFIX}}-XX: <issue title>
      ```
      Reads the ticket (and any `plan` comment), drafts scenario/integration-test stubs with `// TODO:`-style comments. `implement` fills in driver code per WU and makes them green. Pure infrastructure or CI-only changes with no user-facing flows may skip this gate.

   **A note on CI/infrastructure tickets:** for tickets that bring up a new CI/infrastructure target (a new test job, a new emulator/environment, first real-target timing), expect the scope to balloon once real failures start surfacing — this class of issue can only be caught by running against the real target, not in planning. If it does balloon, split the ticket: merge the CI wiring/job setup on its own once it's mechanically correct, and track scenario/flakiness stabilization as a separate follow-up ticket rather than blocking the original PR/MR on every fix.

   **Multi-WU tickets:** if the approved plan (1.3) contains more than one production work unit, see `docs/workflows/MULTI_WU.md` before continuing — it changes how steps 2–12 below are repeated.

2. For features with user-visible screens or interactions: draft UI/widget tests before writing production code:
   - Create new tests covering each new screen and key user flow.
   - Update any existing tests the new screens or UI changes will affect.
   - Present all new and updated test files to the user and wait for approval.
   - Do not continue to step 3 until the user approves the tests.
3. **TDD micro-cycle** — repeat for each logical unit of work within the WU:
   1. **Red** — Write a small set of failing unit tests for one logical unit of work.
      If the unit is a script/hook whose behavior branches on more than ~2
      independent config/state axes (toggles, malformed input, state-file
      presence/staleness, time gaps, etc.), sketch the combinations as a quick
      table first (per `skills/shared/decision-guidelines.md` #3) — this
      surfaces edge cases before review finds them instead of after.
   2. **Green** — Implement the minimum code to make them pass.
      **Opportunistic changes:** If an idea arises to modify existing or in-flight functionality, write the test for that change first. Never modify observable behaviour without a covering test.
      **Scope-expansion discoveries:** If implementation surfaces a question like "does this pattern/bug exist elsewhere in the app too?", do not revise the current ticket's plan (or add new work units) to investigate app-wide — capture the question via `/note` and schedule a dedicated follow-up ticket after this one ships. Small, directly-related fixes discovered along the way can still be folded in with a quick check — it's broadening the ticket's own charter mid-flight that compounds scope.
   3. **Refactor and commit** — Clean up without breaking tests, then commit this micro-cycle as one atomic commit before moving to the next logical unit:
      ```
      git commit -m "feat: <what this logical unit does>"
      ```
      During refactor, look for simple algorithmic improvements that don't hurt readability. Apply them inline; do not defer to a follow-up ticket.

   Each PR/MR accumulates one commit per cycle — reviewable commit-by-commit.
4. Run the project's test suite and linter — fix **all** test failures and warnings/errors before proceeding. A clean lint run is required before committing; do not leave warnings unresolved on the assumption they are pre-existing.
5. After all TDD micro-cycles are complete, apply formatting in a dedicated commit before opening the PR/MR: run your stack's formatter and, if any files changed, stage and commit them separately with a `style:` prefix. This keeps style changes reviewable in isolation from logic changes.
6. Update documentation if affected by the changes:
   - `AGENTS.md`/`CLAUDE.md` — architecture, conventions, or workflow changed
   - `docs/PRODUCT_SPEC.md` — functionality added, removed, or changed
   - `docs/ARCHITECTURE.md` — code structure or dependencies changed
   - `docs/VERSIONING.md` — versioning process impacted
7. **Keep the version file in sync with `docs/CHANGELOG.md`.** Before committing, check that the version name in sync with the latest numbered entry in `CHANGELOG.md`. If a new changelog entry was added in this PR/MR and it carries a user-facing/app-changing tag, update the version file accordingly. Do not touch the build number if CI manages it automatically.

   **Never commit a CHANGELOG entry with no classification tag if your project's `docs/VERSIONING.md` requires one.**
8. Commit all changes with a descriptive message.
9. Push to the remote and open a PR/MR — all in parallel, except the checklist gate below which comes first:

   If this ticket's WU0 was a verification checklist rather than integration scenarios (see `docs/workflows/MULTI_WU.md`), and this is the final WU: run every **[agent]** item yourself and ask the user to confirm every **[human]** item now, before doing any of the following. Do not proceed on an unexecuted checklist.

   - Push the branch to the remote.
   - Open a PR/MR.
   - Move the ticket to **In Review**.
   - Inform the user of the PR/MR URL and open it in the browser.
   - The review loop (step 10) starts automatically once the PR/MR is open, unless the user says otherwise beforehand.
10. **Review loop** — starts automatically once the PR/MR is open (see step 9), unless the user asked to hold; repeat until the user explicitly approves:
    0. **Before starting:** smoke-test the change on your own initiative — confirm it builds/boots, then exercise the specific flow the PR/MR touches. Report the result, then proceed into the loop.
    1. Wait for the review skills (`review`, `audit`), any coverage report, and the user to finish leaving comments.
       - **Immediately after invoking each routed skill, confirm its subagent actually spawned** before moving on to anything else. A skill's routing message is an instruction to act on, not content to just read — treat it the same way you'd treat a TODO you haven't checked off.
    2. For each comment: either fix it in a new commit and push, or post a one-sentence explanation of why the fix will not be implemented, threaded under the original comment.
    3. Check any patch-coverage report. If coverage is below the project threshold, add tests for the uncovered lines where reasonable — skip lines that require disproportionate test infrastructure. Explain skipped lines in a PR/MR comment.
    4. If the cumulative changes since the last review pass are non-trivial (new files, logic changes, interface changes), re-invoke both review skills and return to step 10.1.
    5. Minor fixes (typos, cosmetic, comment wording) do not require a re-review pass.
    6. If this repo has a slower CI suite (integration/E2E) separate from unit tests, dispatch it and confirm it passes before the loop can close, in addition to any local run. A failure in a scenario this PR/MR's own scope must keep green: keep fixing and re-dispatching until it passes. A failure in a scenario **outside** this PR/MR's scope: re-dispatch up to 3 times; if still red on the 3rd attempt, stop and flag it to the user as flakiness to track separately.
    7. The loop ends only when the user explicitly approves ("LGTM", "looks good", "approved", etc.) and any required CI dispatch (step 10.6, when applicable) has passed.
11. Remind the user to compact context after each commit to keep the conversation lean.
12. When the user approves the PR/MR, invoke `debrief` on the current feature branch to capture the retrospective before merging:
    ```
    Invoke the debrief skill for {{ISSUE_PREFIX}}-XX
    ```
    Since a PR/MR is already open for this branch, debrief commits its knowledge-base entry (and any approved workflow/skill changes) directly onto it instead of opening a separate PR/MR.
13. Then invoke the `ship` skill:
    ```
    Invoke the ship skill for PR/MR #<number>
    ```
    The skill moves the ticket to its post-merge state, adds a CHANGELOG entry, regenerates BACKLOG.md, bumps the version, commits onto the feature branch, pushes, and merges.
14. Clear the context now that the ticket is fully shipped, before starting a new ticket.
15. A new ticket may be picked up while the previous one is still being verified.

For tickets whose approved plan contains more than one production work unit (WU1+), see
`docs/workflows/MULTI_WU.md` — it adds pre-implementation WU types (Research-WU, Scenario-WU,
Checklist-WU), branch/PR-per-WU rules, `[wip]` CHANGELOG tagging, and the WU cycle that repeats
steps 2–12 above for each WU.
