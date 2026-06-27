---
name: draft-scenarios
effort: FOCUSED
reasoning: TACTICAL
context: linear
output_style: CONCISE
description: Draft scenarios (integration tests) from a ticket description before implementation. Runs after `plan` (if used) and before `implement`. Scenarios are written against the spec — not reverse-engineered from code — so they compile as stubs and give `implement` a concrete target to fill in and make green.
---

@skills/shared/project-config.md

This skill produces scenario files, not production code.

**Terminology:** a *scenario* is an end-to-end integration test written in the integration test directory (from the project config) using the test harness described there. The terms "scenario" and "integration test" are synonymous in this skill.

---

## Steps

### 1. Fetch the ticket

Fetch the issue (PM mapping: **Fetch issue**), then list its comments (**List comments on issue**) to find any plan comment left by the `plan` skill. Read the description, acceptance criteria, and plan (if present) to understand the expected behaviour.

### 2. Read the test harness

Read the harness file and any existing scenarios in the integration test directory (paths from the project config) for the affected slice or feature area. Note naming conventions, helper patterns, and what is already covered so you do not duplicate.

### 3. Draft scenarios

Produce draft scenario files in the integration test directory (from the project config) using the test harness described there. Cover:

- **Happy path** — the primary flow described in the ticket
- **Unhappy paths** — the most critical failure scenarios: missing data, invalid state, navigation back-stack correctness, cancelled operations, etc.

Write the minimum set of scenarios that verifies the ticket's acceptance criteria. Do not add speculative coverage.

### 4. Present and wait

Show all proposed scenarios to the user and wait for approval. Do not write any files to disk until the user approves. Incorporate any requested changes before writing.

For each scenario present:
1. **Name** — the test name as it will appear in code.
2. **Description** — one sentence on what behaviour it verifies.
3. **Steps** — a numbered list of the interactions and assertions in order (e.g. "1. Seed a stopped pact with an existing note", "2. Open pact detail", "3. Verify note field is pre-populated", "4. Edit the text — Save button becomes enabled", "5. Tap Save — note is persisted in the repository").

This level of detail lets the user verify the test logic before anything is written to disk.

### 5. Write the scenarios

Write the approved scenario files as **stubs**: each test function contains only `// TODO:` comments (or the equivalent comment syntax for the project's test language) describing each step exactly as reviewed in step 4 — no driver calls, no assertions. The stubs must compile against the project harness but verify nothing. The `implement` skill will replace the comments with actual driver code as part of making each scenario green.

### 6. Report back

List the files written and confirm that `implement` can proceed with the commented stubs as its target.

---

## Constraints

- Do not write production code.
- All scenario files must be written under the integration test directory (from the project config).
- Scenario stubs must compile but contain no assertions; `implement` fills in the driver code and makes them green.
- Use the test harness (path and usage from the project config) for all scenario setup.
- Do not duplicate scenarios that already cover the same behaviour.
