# Model Tiers

This project describes what each skill needs from a model using two axes: **Effort Tier** and **Reasoning Depth**. These are stable, provider-agnostic labels — mapped to your available models once at project setup by the `calibrate` skill.

---

## Effort Tiers

| Tier | Meaning |
|---|---|
| **THOROUGH** | Exhaustive analysis. Considers edge cases, synthesises across the whole codebase, slow is fine. |
| **FOCUSED** | Targeted work on a specific scope. Good quality, moderate speed. |
| **RAPID** | Fast pass, surface-level checks, high throughput. |

## Reasoning Depth

| Depth | Meaning |
|---|---|
| **ARCHITECTURAL** | Cross-cutting concerns, system design, long-horizon thinking. |
| **TACTICAL** | Implementation correctness, local patterns, code quality. |
| **MECHANICAL** | Formatting, linting, trivial transforms. |

---

## Skill capability map

### Meta skills — operate on the session and agent layer

| Skill | Effort | Reasoning | Why |
|---|---|---|---|
| `calibrate` | THOROUGH | ARCHITECTURAL | Reasoning about model strengths requires the most capable model available |
| `style` | RAPID | MECHANICAL | Load and apply a communication style definition |

### Product skills — operate on the codebase and product

| Skill | Effort | Reasoning | Why |
|---|---|---|---|
| `plan` | THOROUGH | ARCHITECTURAL | Full codebase read, cross-file design decisions, long-horizon planning |
| `audit` | THOROUGH | TACTICAL | Exhaustive runtime, migration, and edge-case analysis |
| `review` | FOCUSED | ARCHITECTURAL | Targeted architectural review of a PR/MR diff |
| `analyze` | FOCUSED | ARCHITECTURAL | Cross-cutting analytics reasoning scoped to one feature |
| `experiment` | FOCUSED | ARCHITECTURAL | Design a product experiment: hypothesis, metrics, variant spec |
| `implement` | FOCUSED | TACTICAL | Implement a scoped work unit correctly and completely |
| `ship` | RAPID | TACTICAL | Structured housekeeping: close issues, update docs, bump version, merge |
| `summarize` | RAPID | MECHANICAL | Structured PM data fetch and format |

---

## Available models

Models available to this project (set during `setup.sh`):

**{{AVAILABLE_MODELS}}**

The `calibrate` skill reads this list and proposes the mapping below. Re-run `calibrate` whenever the available models change.

---

## Active mapping

_Not yet configured — invoke the `calibrate` skill to populate this section._

---

## How tiers are resolved

Each skill file declares its required tier in its frontmatter:

```yaml
---
name: plan
effort: THOROUGH
reasoning: ARCHITECTURAL
description: ...
---
```

The runtime (Claude Code, Cursor, your agent harness) consults the **Active mapping** table above to select the concrete model for that invocation. If your runtime does not support automatic resolution, set the model manually per invocation based on the table.

---

## Reference: tier-to-model examples

For teams that haven't run `calibrate` yet, or want to cross-check proposals:

| Tier + Depth | Example models |
|---|---|
| THOROUGH + ARCHITECTURAL | Claude Opus, GPT-4o, Gemini 1.5 Pro, Llama 3.1 405B |
| THOROUGH + TACTICAL | Claude Opus, GPT-4o, Gemini 1.5 Pro |
| FOCUSED + ARCHITECTURAL | Claude Sonnet, GPT-4o-mini, Gemini 1.5 Flash, Mistral Large |
| FOCUSED + TACTICAL | Claude Sonnet, GPT-4o-mini, Gemini 1.5 Flash, Mistral Large |
| RAPID + TACTICAL | Claude Haiku, GPT-3.5-turbo, Gemini Flash, Mistral Small |
| RAPID + MECHANICAL | Claude Haiku, GPT-3.5-turbo, Gemini Flash, Mistral Small |

These are starting points. A strong local model may outperform a cloud model for a specific task — `calibrate` will reason about this given your actual list.
