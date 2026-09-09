# Findings protocol

Shared by both tiers — applied to every finding surfaced while walking `light-dimensions.md` or `heavy-dimensions.md`.

## 1. Fix inline, or defer?

Per the Boy Scout Rule — "leave the code cleaner than you found it" ([Laws of Software Engineering](https://lawsofsoftwareengineering.com/laws/boy-scout-rule/)) — fix a finding inline **now** if the fix is small and safe without its own test-writing cycle (a stale doc line, an orphaned file, a glossary entry, a review-by date). If the fix is larger — touches production logic, needs new tests, or is a genuine design change — defer it; do not force-fit it into the checkup's commit.

## 2. Classify deferred findings

Before writing up a deferred finding, classify it with Fowler's Technical Debt Quadrant (deliberate vs. inadvertent × reckless vs. prudent) — most checkup findings are expected to land in **prudent-inadvertent** (a design flaw only visible in hindsight), which is useful context for how urgently the deadline should be set ([Fowler: Technical Debt Quadrant](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html)).

| Quadrant | Typical deadline urgency |
|---|---|
| Reckless-deliberate | Immediate — this is known-bad code shipped under pressure |
| Reckless-inadvertent | Soon — a mistake that's now understood |
| Prudent-deliberate | Planned — a conscious trade-off with a known payoff date |
| Prudent-inadvertent | Normal — most checkup findings; deadline set by judgement, not urgency |

## 3. Write it up

Every finding — inline-fixed or deferred — gets a block in the run's `docs/knowledge/checkups/CHK-YYYY-MM-DD-<tier>.md` (from `TEMPLATE.md`), under the dimension that surfaced it:

```markdown
### <Dimension name>

- **Finding:** <what was found>
- **Debt quadrant:** deliberate/inadvertent × reckless/prudent
- **Disposition:** fixed inline (commit `<sha>`) | deferred — see ledger, deadline `YYYY-MM-DD`
- **Graduation candidate:** yes/no — if yes, name the mechanical check this dimension could graduate into
```

## 4. Ledger deadline-line format

Deferred findings get a row in `docs/knowledge/checkups/LEDGER.md`'s **Open findings** table — no individual PM ticket is filed (per ADR-0001):

```markdown
| CHK-YYYY-MM-DD-<tier>-<n> | YYYY-MM-DD | light\|heavy | <dimension> | <quadrant> | <one-line summary> | YYYY-MM-DD | [CHK-YYYY-MM-DD-<tier>](CHK-YYYY-MM-DD-<tier>.md) |
```

`ID` is the write-up filename plus a sequence number (`-1`, `-2`, …) if more than one deferred finding shares a run. `Deadline` is a concrete date — set by judgement (see the quadrant table above), never left open-ended; this deliberately deviates from "fix when back in that code area," which has no natural trigger for a small team.

When a deferred finding is later resolved (in this run or a future one), move its row from **Open findings** to **Resolved findings**, adding the resolution date.

## 5. Discovery outcome — graduation candidates

If a dimension turns out to be mechanically measurable (a lint rule, a CI check, a script), do not automate it in place — flag it as a graduation candidate in the write-up (see the template block above) so a future ticket can wire it into CI. This is how the manual checklist is meant to shrink over time.

## 6. Scheduling ledger findings into tickets

When it's time to turn deferred ledger findings into actual implementation work, first do a lightweight dependency-graph pass across the findings being scheduled — find real dependency/impact relationships, not just "same dimension" — to determine both **grouping and order**. Default to **one small ticket per finding** rather than bundling multiple findings into a single ticket — small, few-hour-sized tickets are easier to schedule opportunistically and don't require re-deriving the dependency graph from scratch each time. Use the graph to decide the tickets' working order (a finding whose fix shrinks or simplifies another's surface should ship first), and only bundle findings into one ticket when there is a **real, direct dependency** between them (one finding's fix would be redone or complicated by doing another first) — not merely "same dimension" or "same code area." When bundling, state the dependency explicitly in the ticket description before work starts.
