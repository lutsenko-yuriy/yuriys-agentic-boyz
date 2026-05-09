# Experiment Registry

All product experiments are tracked here. One file per experiment under this directory.

## Stack
- **Running experiments:** {{EXPERIMENT_TOOL}} (e.g. Firebase Remote Config + Firebase A/B Testing, Statsig, LaunchDarkly, or PostHog)
- **Tracking outcomes:** This registry (one `.md` file per experiment)
- **When to revisit dedicated tooling:** when running >5 concurrent experiments or needing richer governance/analysis

## Starting an experiment

1. Pick the next sequential `EXP-NNN` ID from the index table below.
2. Copy `docs/experiments/TEMPLATE.md` to `docs/experiments/EXP-NNN-<short-name>.md`.
3. Fill in the hypothesis, setup, and metrics sections. Leave Decision and Learnings blank.
4. Add a row to the Index table with status `running`.

## Statuses

| Status | Meaning |
|---|---|
| `running` | Experiment is live and collecting data |
| `won` | Hypothesis confirmed — change shipped to 100% |
| `lost` | Hypothesis rejected — variant rolled back |
| `abandoned` | Stopped early (low traffic, flawed setup, changed priorities) — no conclusive result |

## Index

| ID | Name | Status | Primary metric result | Decision date |
|---|---|---|---|---|
| _(no experiments yet)_ | | | | |
