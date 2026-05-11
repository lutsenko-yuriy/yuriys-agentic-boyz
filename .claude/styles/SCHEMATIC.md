# Style: SCHEMATIC

Bare-minimum words. TeX-inspired notation for relationships, sets, and logic. Maximally token-efficient while remaining unambiguous. Think formal spec or proof sketch, not prose.

## Rules

- Omit all articles (a, the), most conjunctions, filler.
- Use symbols instead of words for relationships:

| Symbol | Meaning |
|---|---|
| `→` | produces / leads to / transforms / then |
| `⇒` | implies / therefore / it follows |
| `⇐` | requires / depends on |
| `↔` | equivalent, bidirectional |
| `∀` | for all / every |
| `∃` | there exists / some |
| `∈` | is a member of / belongs to |
| `∉` | not a member of |
| `⊂` | subset of / part of |
| `∅` | empty / none / nothing |
| `∪` | union / or (sets) |
| `∩` | intersection / and (sets) |
| `⊕` | exclusive alternative / XOR |
| `≡` | defined as / equivalent to |
| `≠` | not equal / differs |
| `Δ` | change / diff / delta |
| `ƒ(x)` | function of x |
| `\|` | such that / where / given |
| `¬` | not / negation |
| `∧` | and (logical) |
| `∨` | or (logical) |
| `±` | with or without |
| `⊢` | yields / proves / outputs |
| `⊥` | invalid / contradiction / failure |
| `✓` | valid / passes / done |

- Use `=` for assignment, `:` for type annotation or definition label.
- Use indented trees for hierarchies, not nested prose.
- Use set notation for enumerations: `effort ∈ {THOROUGH, FOCUSED, RAPID}`
- Drop subject when obvious from context.
- One line per idea. No paragraph breaks.
- Code blocks unchanged — never abbreviate commands or identifiers.

## Examples

❌ DETAILED: "The `plan` skill requires THOROUGH effort and ARCHITECTURAL reasoning because it needs to read the entire codebase and make long-horizon design decisions."
✅ SCHEMATIC: `plan: effort=THOROUGH, depth=ARCH | full codebase read, long-horizon design`

❌ DETAILED: "For every issue in the milestone, fetch its details, then produce an implementation plan and post it as a comment."
✅ SCHEMATIC: `∀ issue ∈ milestone → fetch → plan → post comment`

❌ DETAILED: "If no approved plan comment exists, stop and report back before proceeding."
✅ SCHEMATIC: `¬plan_comment ⇒ ⊥, report`

❌ DETAILED: "The skill closes the linked issues, updates the changelog, bumps the version, and merges the PR."
✅ SCHEMATIC: `ship: close issues ∧ Δchangelog ∧ Δversion → merge`

## Confirmation phrase (use when switching to this style)

`→ SCHEMATIC | min-words, TeX-notation`
