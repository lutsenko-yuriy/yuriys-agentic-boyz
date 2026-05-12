# Style: SCHEMATIC

TeX-math notation fused with Haskell-style syntax. Logic and sets from TeX; types, composition, binding, and guards from Haskell. Zero prose. Every idea is an expression.

## When to use

- **Agent-to-agent communication** — skill outputs consumed by another skill or agent that understands SCHEMATIC notation.
- **Workflow and pipeline specs** — describing how skills chain together (`>>=`, `∧`, `>>`).
- **Type-level reasoning** — expressing what a skill accepts and returns, constraints, and invariants.
- **Audience:** another agent or a developer who knows the notation. Do *not* use with people unfamiliar with SCHEMATIC — switch to CONCISE or DETAILED instead.

---

## Core syntax

### Types and signatures
```
name :: InputType → OutputType
skill :: Issue → Plan
```

### Function composition (sequencing without data passing)
```
f ∘ g        -- apply g then f (math order)
f . g        -- same, Haskell order
```

### Monadic sequencing (pass result forward)
```
fetch i >>= plan >>= postComment   -- chain with result
fetch i >> notify                  -- chain, discard result
```

### Lambda
```
λi. fetch i >>= plan
\i -> fetch i >>= plan
```

### Guards
```
f x
  | p x       = a
  | q x       = b
  | otherwise = ⊥
```

### Case
```
case x of
  A → ...
  B → ...
  _ → ⊥
```

### Let / where
```
let x = expr in body

body
  where
    x = expr
    y = expr
```

### List comprehension
```
[f x | x ← xs, p x]
```

### Maybe / Either for optional or error values
```
Just x       -- value present
Nothing      -- absent / skip
Right x      -- success
Left e       -- failure / error
```

---

## TeX symbol set

| Symbol | Meaning |
|---|---|
| `∀` | for all |
| `∃` | there exists |
| `∈` | member of |
| `∉` | not member of |
| `⊂` | subset of |
| `∅` | empty / none |
| `¬` | not |
| `∧` | and (also: parallel execution) |
| `∨` | or |
| `⇒` | implies / therefore |
| `⇐` | requires / depends on |
| `↔` | if and only if |
| `≡` | defined as / equivalent |
| `≠` | not equal |
| `Δ` | change / diff |
| `⊥` | failure / invalid / abort |
| `⊤` | always true / unconditional |
| `⊢` | yields / proves |
| `{x \| P x}` | set comprehension |

---

## Rules

- No articles, no filler, no narrative.
- One expression per line; indent for scope.
- Use `::` for type annotation; use `→` or `->` for function arrows.
- Use `>>=` when the result of one step is the input of the next.
- Use `>>` when steps are sequential but the prior result is discarded.
- Use `∘` / `.` for pure composition (no effects).
- Use `∧` for steps that run in parallel.
- Use guards `| cond = ...` instead of if/else prose.
- `⊥` terminates — always follow with a quoted reason string.
- Code blocks unchanged — never abbreviate identifiers or shell commands.

---

## Examples

**Describing a skill's type:**
```
plan :: Issue → Plan
  | effort = THOROUGH, depth = ARCH
```

**A workflow pipeline:**
```
workflow = analyze >> plan >>= implement >>= (review ∧ audit) >>= ship
```

**Conditional logic:**
```
proceed
  | ∃ c ∈ comments. approved c = implement
  | otherwise                  = ⊥ "no approved plan"
```

**For-all over a collection:**
```
∀ i ∈ milestone. fetch i >>= plan >>= postComment
```

**A skill capability table:**
```
calibrate :: [Model] → TierMapping
  | effort = THOROUGH, depth = ARCH
  | self-application ⇒ use max(models)

summarize :: () → Backlog
  | effort = RAPID, depth = MECH
```

**Parallel reviews:**
```
onPROpen n = review n ∧ audit n
  where
    review :: PR → ArchReport   -- FOCUSED ∘ ARCH
    audit  :: PR → RiskReport   -- THOROUGH ∘ TAC
```

**Style switching:**
```
case style of
  DETAILED   → prose ∘ full
  CONCISE    → bullets ∘ abbrev ∘ conclusionFirst
  SCHEMATIC  → TeX ∘ Haskell
```

---

## Confirmation phrase (use when switching to this style)

```
style :: () → SCHEMATIC
  where SCHEMATIC ≡ TeX ∘ Haskell | ¬prose
```
