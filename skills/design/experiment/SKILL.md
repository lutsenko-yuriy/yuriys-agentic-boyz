---
name: experiment
effort: FOCUSED
reasoning: ARCHITECTURAL
description: Design a product experiment. Given a hypothesis or feature idea, produces a full experiment spec (hypothesis, audience, feature flag, metrics, stop rule), creates the experiment file under docs/experiments/, and updates the registry index. Invoke as "Invoke the experiment skill for EXP-NNN: <hypothesis>" or "/experiment <idea>". Waits for approval before writing files.
---

## Steps

### 1. Understand the hypothesis

Read the user's input. Extract or infer:

- The **change** being tested (what is different in the variant)
- The **outcome** expected (the metric that should move)
- The **audience** (who sees the variant — new users, logged-in users, a percentage)
- The **rationale** (why this change should produce that outcome)

If any of the four is unclear, ask one focused question before proceeding.

### 2. Read the experiment registry

Read `docs/experiments/README.md` to:

1. Find the highest existing `EXP-NNN` ID in the Index table.
2. Assign the next sequential ID (e.g. if the last is `EXP-003`, use `EXP-004`).
3. If the table shows "no experiments yet", start at `EXP-001`.

### 3. Propose the experiment spec

Present a draft spec for approval. Do **not** write any files yet.

```
EXP-NNN — <short name>

Hypothesis
  We believe that [change] will cause [outcome] for [audience] because [rationale].

Setup
  Audience:    <e.g. 20% of new sign-ups>
  Feature flag: <e.g. exp_nnn_<short_name>>
  Ramp plan:   <e.g. 10% → 50% → 100% or kill>
  Stop rule:   <e.g. minimum 500 users or 2 weeks, whichever comes first>

Metrics
  Primary:   <metric name> — baseline: <value or "unknown">
  Guardrail: <metric name> — baseline: <value or "unknown">

Analytics events needed
  <list any new events or properties required; "none" if existing events cover it>
```

Ask: **"Does this look right? Any adjustments before I create the files?"**

Wait for explicit approval or requested changes. Iterate until approved.

### 4. Create the experiment file

Once approved, copy `docs/experiments/TEMPLATE.md` to `docs/experiments/EXP-NNN-<short-name>.md` and fill in all sections with the approved spec. Leave Decision and Learnings blank.

Determine the short name: lowercase, hyphens, ≤ 4 words (e.g. `onboarding-skip-button`).

### 5. Update the registry index

Open `docs/experiments/README.md` and add a row to the Index table:

```
| EXP-NNN | <short name> | `running` | | |
```

Replace the "no experiments yet" placeholder row if it is still present.

### 6. Flag analytics gaps (if any)

If new analytics events are required (identified in step 3):

- Note which events are missing from `docs/ANALYTICS_EVENTS.md`.
- Tell the user: "These events need to be added before the experiment can be instrumented — invoke the `analyze` skill or add them manually to `docs/ANALYTICS_EVENTS.md`."

Do **not** add the events yourself; analytics planning is the `analyze` skill's responsibility.

### 7. Confirm

Report:
- File created: `docs/experiments/EXP-NNN-<short-name>.md`
- Registry updated: `docs/experiments/README.md`
- Next step: instrument the feature flag in code, then invoke `implement` for the variant

---

## Notes

- The experiment skill designs and registers experiments; it does not implement them. Implementation follows via the normal `plan` → `implement` workflow, scoped to the experiment variant.
- The feature flag name convention is `exp_<id_lowercase>_<short_name>` (e.g. `exp_001_onboarding_skip`).
- If the user provides an explicit `EXP-NNN` ID (e.g. to backfill an experiment started manually), use that ID instead of auto-assigning.
- Experiments that require net-new analytics events must go through `analyze` before implementation begins so that `docs/ANALYTICS_EVENTS.md` stays accurate.
