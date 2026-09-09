# Light-tier dimensions

Due the 1st of every calendar month, tracked as "not yet done this month" — see [ADR-0001](../../../../docs/knowledge/decisions/ADR-0001-two-tier-periodic-code-quality-checkup.md). Walk these five in order.

## 1. Unused functionality

Run any dead-code/lint tooling this project has; otherwise grep for exports, handlers, or event classes with no remaining caller. Cross-check any analytics-event catalogue for events defined but never fired, and feature-flag-gated entry points shipped but seemingly unused. As product owner, question features that may not earn their keep.

*Grounding: product-analytics "kill condition" practice — doesn't retroactively help shipped features but surfaces retirement candidates ([Userpilot](https://userpilot.com/blog/product-feature-analysis/)).*

## 2. Scenario quality

Review the project's integration/end-to-end test suite: do scenarios still map to current `docs/PRODUCT_SPEC.md` flows? Any skipped/commented/`TODO` scenarios, redundant overlap, or assertions that assert nothing meaningful?

*Grounding: internal heuristic tied to `/draft-scenarios` conventions — no strong external precedent, noted as such.*

## 3. Glossary/naming drift

If the project maintains a canonical-terms glossary (e.g. `docs/GLOSSARY.md`), diff its terms and known aliases against current code identifiers and UI strings; flag code terms absent from the glossary and aliases that crept back in. Skip this dimension if the project has no such glossary.

*Grounding: DDD ubiquitous-language drift is expected as implementation solidifies — the glossary needs periodic review, not a one-time write ([Fowler: Ubiquitous Language](https://martinfowler.com/bliki/UbiquitousLanguage.html)).*

## 4. Doc-reality drift

Sampled read of the project's key docs (architecture, product spec, feature-flag catalogue, CI pipeline docs — whichever of these the project maintains) against current code: do described flags, events, layers, and pipeline mechanics still exist and match? Sampled, not exhaustive — mechanical staleness detection is out of scope.

*Grounding: docs-as-code staleness detection normally assumes CI/mechanical enforcement, which doesn't fit a small-team monthly cadence ([Docsie](https://www.docsie.io/blog/glossary/documentation-drift/)).*

## 5. Feature-flag lifecycle

If the project uses feature flags/kill-switches, for each one: still needed? how old? assign or verify a review-by date; flag stale kill-switches for removal. Skip this dimension if the project has no feature-flag mechanism.

*Grounding: feature-flag audit practice — an explicit per-flag expiration/review-by date, because stale flags compound ([Statsig](https://www.statsig.com/perspectives/tips-for-unused-feature-flag-clean-up) · [FlagShark](https://flagshark.com/blog/feature-flag-lifecycle-creation-cleanup-5-stages/)).*
