---
name: calibrate
effort: THOROUGH
reasoning: ARCHITECTURAL
description: One-time project setup skill. Reads the available models listed in docs/MODEL_TIERS.md, proposes an optimal mapping from every Effort Tier + Reasoning Depth combination to a specific model, waits for user approval or adjustments, then writes the agreed mapping into docs/MODEL_TIERS.md. Invoke once after setup.sh, before the first working session. This skill itself requires THOROUGH + ARCHITECTURAL capability to reason about model strengths.
---

This skill requires **THOROUGH + ARCHITECTURAL** capability — use the most capable model available when invoking it. The mapping you produce governs every other skill in this project, so the reasoning must be exhaustive and well-justified.

---

## Steps

### 1. Read the context

Read `docs/MODEL_TIERS.md` in full. Note:
- The Effort Tier and Reasoning Depth definitions
- The skill capability map (which skills need which combination)
- The available models listed under `## Available models`

### 2. Characterise each available model

For every model in the available list, reason across these dimensions:

| Dimension | What to assess |
|---|---|
| **Context window** | Can it hold a full codebase read? Relevant for THOROUGH tasks. |
| **Reasoning quality** | Does it handle multi-step, cross-file analysis? Relevant for ARCHITECTURAL. |
| **Code understanding** | Does it track local patterns and correctness? Relevant for TACTICAL. |
| **Speed / cost** | Is it fast and cheap enough for high-frequency FOCUSED/RAPID work? |
| **Instruction following** | Does it reliably follow structured multi-step procedures? |

If you lack benchmark data for a model, reason from its known tier (e.g. "large frontier model", "mid-size open-weight", "fast small model") and state your uncertainty explicitly.

### 3. Propose the mapping

Map each combination used by the project's skills to the single best available model. The combinations are:

| Effort | Reasoning | Used by |
|---|---|---|
| THOROUGH | ARCHITECTURAL | `plan`, `calibrate` |
| THOROUGH | TACTICAL | `audit` |
| FOCUSED | ARCHITECTURAL | `review`, `analyze` |
| FOCUSED | TACTICAL | `implement` |
| RAPID | TACTICAL | `ship` |
| RAPID | MECHANICAL | `summarize` |

Rules for the proposal:
- Each combination must map to exactly one model from the available list.
- THOROUGH combinations must map to the most capable model(s) available — do not assign a faster/cheaper model to save cost at the expense of quality here.
- FOCUSED combinations should balance quality and speed.
- RAPID combinations should prioritise speed; correctness matters but deep reasoning is not required.
- Different combinations may map to the same model if the available list is short.
- Justify every assignment in one sentence.

Present the proposal in this format:

```
## Proposed model tier mapping — {{PROJECT_NAME}}

Available models: {{AVAILABLE_MODELS}}

| Effort | Reasoning | Model | Justification |
|---|---|---|---|
| THOROUGH | ARCHITECTURAL | <model> | <one sentence> |
| THOROUGH | TACTICAL | <model> | <one sentence> |
| FOCUSED | ARCHITECTURAL | <model> | <one sentence> |
| FOCUSED | TACTICAL | <model> | <one sentence> |
| RAPID | TACTICAL | <model> | <one sentence> |
| RAPID | MECHANICAL | <model> | <one sentence> |

### Notes
<Any caveats — e.g. "Only one model was provided so all tiers map to it", or "THOROUGH+ARCHITECTURAL may be slow for large codebases with this model".>
```

### 4. Wait for approval

Present the proposal and ask:

> "Does this mapping look right? You can adjust any row before I write it. Reply with the approved table or describe your changes."

Do not proceed until the user explicitly approves or provides corrections.

### 5. Write the approved mapping

Open `docs/MODEL_TIERS.md` and replace the content of the `## Active mapping` section with the approved table plus a datestamp:

```markdown
## Active mapping

_Last updated: YYYY-MM-DD._

| Effort | Reasoning | Model |
|---|---|---|
| THOROUGH | ARCHITECTURAL | <model> |
| THOROUGH | TACTICAL | <model> |
| FOCUSED | ARCHITECTURAL | <model> |
| FOCUSED | TACTICAL | <model> |
| RAPID | TACTICAL | <model> |
| RAPID | MECHANICAL | <model> |
```

Do not modify any other section of `docs/MODEL_TIERS.md`.

### 6. Report back

Confirm the mapping has been written and remind the user:

> "Model tier mapping saved to docs/MODEL_TIERS.md. Each skill declares its required effort + reasoning in its frontmatter — your runtime should consult this mapping to select the right model. Re-run `calibrate` any time your available models change."
