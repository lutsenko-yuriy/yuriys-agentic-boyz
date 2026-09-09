# Architecture Decision Records

Standing decisions — not experiments, not ticket retrospectives — tracked here. One file per decision under this directory. Mirrors the `docs/experiments/` registry pattern.

## When to write an ADR

Write one when a ticket's research or implementation concludes in a decision that should be discoverable **without knowing which ticket produced it** — e.g. "we chose the MIT licence," "we chose this docs structure." Day-to-day research notes and ticket retrospectives stay in `docs/knowledge/notes/{{ISSUE_PREFIX}}-XX.md`; an ADR is the short, dated, standalone record of the *decision itself*, linking back to the ticket note for full rationale.

## Starting an ADR

1. Pick the next sequential `ADR-NNNN` ID from the index table below (4-digit, zero-padded, e.g. `ADR-0001`).
2. Copy `docs/knowledge/decisions/TEMPLATE.md` to `docs/knowledge/decisions/ADR-NNNN-<short-name>.md`, where `<short-name>` is a kebab-case slug (mirrors branch naming, e.g. `feature/{{ISSUE_PREFIX}}-XX-<short-description>`).
3. Replace the template's H1 with a one-sentence description of the decision, commit-message style (e.g. "add per-channel distribute toggles to manual dispatch") — not just a noun-phrase title.
4. Fill in Context, Decision, Alternatives considered, Related ticket, and Date. When a decision bullet rests on an external source, cite it inline next to that bullet — not batched into the Context paragraph. Each claim should be verifiable where it's made, without cross-referencing elsewhere in the doc.
5. Add a row to the Index table, using the same one-sentence description in the Description column.

## ID format

`ADR-NNNN` — 4-digit, zero-padded, sequential. Deliberately wider than `docs/experiments/`'s 3-digit `EXP-NNN`: a project can rack up hundreds of tickets within months, and an ADR ID format shouldn't need to change to keep up.

## Statuses

| Status | Meaning |
|---|---|
| `proposed` | Drafted, not yet acted on |
| `accepted` | In effect |
| `rejected` | Considered, not adopted |
| `superseded` | Replaced by a later ADR — link the replacement |

## Index

| ID | Description | Status | Date | Related ticket |
|---|---|---|---|---|
| ADR-0001 | run a two-tier (light/heavy) periodic checkup for non-mechanical code quality dimensions | `accepted` | 2026-09-09 | {{ISSUE_PREFIX}}-XX |
| ADR-0002 | build a single-pass dialectical (thesis/antithesis/synthesis) research skill, steelman-bounded, over six other candidate methodologies | `accepted` | 2026-09-09 | {{ISSUE_PREFIX}}-XX |
