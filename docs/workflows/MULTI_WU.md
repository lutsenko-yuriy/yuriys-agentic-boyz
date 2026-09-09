# Multi-WU Tickets

Appendix to `docs/workflows/FEATURE.md` — read this when the approved plan (that workflow's
step 1.3) contains more than one production work unit (WU1+). Follow these rules in addition
to the standard workflow's steps 2–12, which each WU repeats in full.

## WU-splitting guidelines

SHOULD-level guidelines for dividing a ticket into work units during planning, and for handling
a WU0 scenario-stub commit.

1. **Isolate UI/visual-design work into its own WU, and expect it to change a lot mid-development.** A UI-heavy WU (animation choreography, layout, visual polish) can't be fully nailed down on paper — seeing it running is what surfaces the real design. Don't treat that churn as a planning failure; plan for it by keeping UI-heavy work in its own WU rather than bundling it with logic/data WUs whose scope is comparatively stable.

2. **A WU0 stub must not delete scenario coverage for behavior still shipping in production.** The standard WU0 pattern (scenario stubs only, no driver code) works cleanly for additive features, where the old behavior keeps running and old tests keep passing alongside new stubs. It breaks when a stub *replaces* a scenario that verifies behavior still live in `main` — deleting the old test removes real coverage before the new behavior exists to cover it. Instead: mark the superseded scenario clearly as legacy (e.g. a `_legacy` suffix or a labeled group) and keep it running against the still-current behavior; only delete it in the WU that actually retires the underlying behavior, in the same commit.

3. **Longer-term: a dedicated designer (human or agent) could reduce this volatility at the source**, since the churn traces back to UI decisions not being settled before implementation starts, not to the WU-splitting process itself. Not staffed yet — flagged here as a direction, not a commitment.

## Pre-implementation WUs

**Research-WU (optional) — then Scenario-WU or Checklist-WU**

If planning surfaces a design choice that would benefit from external validation (precedent from other apps/tools, a published guideline, an established best practice), `plan` proposes a **Research-WU** as the ticket's first WU, running before Scenario-WU/Checklist-WU. It runs `/research` (or an equivalent bounded, cited check) and writes findings to the ticket's knowledge note. No separate branch or PR/MR — same as Checklist-WU below. **Omit it when the ticket is genuinely novel** — no comparable precedent exists to research.

**Scenario-WU** — for tickets with a user-facing flow `draft-scenarios` can assert against: after scenarios are approved and written (`FEATURE.md` step 1.6), commit them to `feature/{{ISSUE_PREFIX}}-XX-WU0-scenarios`, push, and open a PR/MR titled `test(WU0): integration scenarios ({{ISSUE_PREFIX}}-XX)`. Use `[test]` as the CHANGELOG classification tag. Merge WU0 directly — no `ship`, no version bump. Each subsequent WU's plan entry lists which scenarios it makes green.

**Checklist-WU** — for everything else (meta/skills/docs work, backend-only changes, or any ticket where scenario generation is skipped): `plan` writes this WU as a **verification checklist** in the plan's Test strategy section instead — a plan-only artifact, no separate branch or PR/MR. Each item is tagged **[agent]** (the agent runs it itself) or **[human]** (needs a person's judgment). **Run it before opening the final WU's PR/MR** (`FEATURE.md` step 9) regardless of whether `/implement` was formally invoked for that WU — this convention exists specifically because process/meta tickets are often worked directly in the orchestrating session rather than through `/implement`, so the enforcement point cannot live solely in that skill.

Research-WU, Scenario-WU, and Checklist-WU are named, not numbered — they're pre-implementation units that never carry production code. Everything after them keeps the existing numeric naming (WU1, WU2, …), unchanged by this convention.

## One WU = one branch = one PR/MR

Each WU gets its own branch (`feature/{{ISSUE_PREFIX}}-XX-WUN-<short>`, where N is the WU number from the plan's WU table) created fresh from `origin/main`. Never reuse a branch from a previous WU. Branch names are pre-named in the plan comment's WU table so the full mapping is visible from day one.

## CHANGELOG tags for intermediate WUs

Use `[wip]` as the classification tag for all intermediate WU CHANGELOG entries — every WU except the final one. `[wip]` suppresses builds and distribution so testers do not receive partial builds mid-ticket. The final WU uses whichever tag actually reflects what the ticket produced: a user-facing/app-changing tag if it's user-facing (this is when CI builds and distributes, and "What's New" aggregates all user-facing content back to the last published tag), or an internal-only tag if the ticket is pure process/CI/tooling work end-to-end with nothing user-facing to ship.

## WU cycle (WU1 onwards)

For each WU in sequence:
1. Create a fresh branch from the latest `origin/main` using the branch name from the plan table.
2. Follow `FEATURE.md` steps 2–11 (UI tests, TDD cycles, validate, format, PR/MR, review loop). The full review loop (step 10) — review, audit, coverage, and user sign-off — is mandatory for every WU PR/MR without exception.
3. **If this is the final WU** (the one that completes the ticket): invoke `debrief` now (`FEATURE.md` step 12), before shipping — the same order as the single-WU flow. **If this is an intermediate WU**: skip debrief; it runs exactly once, at the final WU.
   - **If a new WU gets added mid-ticket** (a scope addition discovered during review, not part of the original plan table): immediately update every place that names the "final WU" — the ticket's knowledge-base note and any PM comment framing an earlier WU as final — in the same action that adds the new WU. Do not defer this correction to the next ship/debrief; a stale "final WU" marker is what causes ordering confusion and premature-completion mistakes.
4. Invoke `ship` (`FEATURE.md` step 13).
5. **Hard checkpoint:** after `ship` merges, explicitly tell the user to compact context now, before continuing — state it as its own message and wait for it to happen.
6. Fetch `origin/main` and start the next WU from the freshly updated tip.

## Merge authority when a WU runs in a subagent

When `implement`/`ship` for a WU is delegated to a subagent, that subagent should only
treat an approval it receives directly, in its own thread, as satisfying `FEATURE.md`
step 10.7's explicit-approval gate — not an orchestrator relaying "the user said X" from
a separate session. This is a feature, not a bug: a second-hand approval claim is not
independently verifiable by the subagent. If a subagent declines to merge on those
grounds, don't push it to override the safeguard — instead invoke `ship` yourself in the
main session, where the user's actual approval message is present in the transcript.
