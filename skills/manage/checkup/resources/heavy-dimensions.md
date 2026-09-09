# Heavy-tier dimensions

Due the 14th of every quarter-anchor month (Jan/Apr/Jul/Oct), tracked as "not yet done this quarter" — see [ADR-0001](../../../../docs/knowledge/decisions/ADR-0001-two-tier-periodic-code-quality-checkup.md). These four require a full sweep of the whole project; walk them in order.

## 6. Readability & structural clarity

Full sweep for long or deeply-nested methods, high branching, duplicated logic, oversized modules/components, and unclear names. Optional manual static-analysis/cyclomatic-complexity spot-check with whatever tool your language ecosystem offers; if a threshold proves consistently meaningful, note it as a graduation candidate for a future automated check (see `resources/findings-protocol.md`) — do not wire CI here.

*Grounding: cyclomatic complexity is a standard, tool-supported metric across most language ecosystems, confirming this dimension could later graduate to CI.*

## 7. Cross-screen/cross-surface UX consistency

Full-interface heuristic evaluation, single agent-assisted pass (adapted from NN/g's 3–5-evaluator method): apply Nielsen's 10 heuristics, especially #4 "Consistency and standards" — spacing, component styles, terminology, and platform parity across each surface.

*Grounding: NN/g heuristic evaluation is the closest analog for cross-screen consistency; adapted to a single evaluator here ([NN/g](https://www.nngroup.com/articles/how-to-conduct-a-heuristic-evaluation/)).*

## 8. Accessibility

Manual audit pass: semantic labels on interactive elements, tap/click-target sizes, colour contrast, text scaling, and screen-reader traversal — complementing (not replacing) any automated scan.

*Grounding: manual accessibility audits are commonly run quarterly/annually for depth alongside continuous automated scans ([TheWCAG](https://www.thewcag.com/accessibility-audit-guide)).*

## 9. Knowledge-corpus bookmark health

Quarterly re-bookmarking of the entire knowledge base. Reads `docs/knowledge/notes/BOOKMARKS.md` and scans all `docs/knowledge/notes/*.md` files for bookmark usage. Flag any bookmarks that are:
- Unused (no notes reference them)
- Obsolete (referenced in notes, but no longer make sense in context)
- Redundant (multiple synonyms for the same concept)

Propose new bookmarks when a recurring pattern emerges from the corpus that doesn't fit existing ones.

Also spot-check notes filed under `bookmarks: []` ("reviewed, nothing noteworthy") against their actual content — since `TEMPLATE.md` seeds this as the default, a note that was never really reviewed is indistinguishable from one that genuinely has nothing worth tagging. This bucket is where that gap would hide.

*Grounding: this is an emergent taxonomy; periodic review ensures it stays aligned with the project's actual pain points and patterns.*
