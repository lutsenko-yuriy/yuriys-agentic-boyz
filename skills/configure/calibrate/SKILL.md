---
name: calibrate
effort: THOROUGH
reasoning: ARCHITECTURAL
output_style: DETAILED
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

If you lack benchmark data for a model, reason from its known tier (e.g. "large frontier model", "mid-size open-weight", "fast small model") and state your uncertainty explicitly. For **LM Studio** models the identifier comes from the LM Studio UI or `GET http://localhost:1234/v1/models`; treat a quantised local model as roughly 1–2 tiers below its full-precision cloud equivalent (e.g. a Q4 8 B model ≈ RAPID tier) unless the user confirms otherwise.

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

Open `docs/MODEL_TIERS.md` and replace the content of the `## Active mapping` section with the approved table plus a datestamp. Include the **Claude Code alias** column (`opus` / `sonnet` / `lm-studio`) so command stubs can read it:

```markdown
## Active mapping

_Last updated: YYYY-MM-DD._

| Effort | Reasoning | Model | Claude Code alias |
|---|---|---|---|
| THOROUGH | ARCHITECTURAL | <model> | `opus` or `sonnet` or `lm-studio` |
| THOROUGH | TACTICAL | <model> | `opus` or `sonnet` or `lm-studio` |
| FOCUSED | ARCHITECTURAL | <model> | `opus` or `sonnet` or `lm-studio` |
| FOCUSED | TACTICAL | <model> | `opus` or `sonnet` or `lm-studio` |
| RAPID | TACTICAL | <model> | `opus` or `sonnet` or `lm-studio` |
| RAPID | MECHANICAL | <model> | `opus` or `sonnet` or `lm-studio` |
```

Alias rules: `opus` for claude-opus-*; `sonnet` for claude-sonnet-*; `haiku` for claude-haiku-*; `lm-studio` for any local/MLX model.

Do not modify any other section of `docs/MODEL_TIERS.md`.

### 5a. Update command stubs

After writing `docs/MODEL_TIERS.md`, update every `.claude/commands/*.md` stub that has changed alias. The stub format is:

**Routing rule — only spawn when the target model differs from the current session model:**

- **Spawn up** (`opus`) — target is more capable than the session model; use the Agent routing stub below.
- **Run locally** (same alias as session, e.g. `sonnet` when session is sonnet) — spawning adds cold-start overhead with no benefit; use the passthrough format (`@skills/... + $ARGUMENTS`).
- **Route to local model** (`lm-studio`) — target is a local LM Studio model; use the script stub.

**Agent routing stub format (use when spawning up to a more capable model):**
```markdown
Route this invocation to a subagent. **Do not execute the skill yourself.**

**Skill:** <name>
**Tier:** <EFFORT> + <REASONING>
**Model alias:** <alias>

Steps:
1. Read `skills/<path>/SKILL.md` using the Read tool.
2. Spawn an Agent with:
   - `model`: `"<alias>"`
   - `prompt`: full content of the skill file[, followed by the arguments below].

[**Arguments:**
$ARGUMENTS]
```

**Passthrough format (use when target model == session model):**
```markdown
@skills/<path>/SKILL.md

$ARGUMENTS
```

**Script stub format (use for lm-studio alias):**

_With `$ARGUMENTS` (skills that take user-supplied input):_
```markdown
Run via Bash: `python3 scripts/skill_router.py skills/<path>/SKILL.md --args '$ARGUMENTS'`
If the script exits non-zero (LM Studio unavailable or model not loaded), fall back to reading `skills/<path>/SKILL.md` and executing it yourself.

$ARGUMENTS
```

_Without `$ARGUMENTS` (skills that need no user input):_
```markdown
Run via Bash: `python3 scripts/skill_router.py skills/<path>/SKILL.md`
If the script exits non-zero (LM Studio unavailable or model not loaded), fall back to reading `skills/<path>/SKILL.md` and executing it yourself.
```

Only update stubs whose alias changed — do not touch stubs that are already correct.

### 6. Report back

Confirm the mapping has been written and remind the user:

> "Model tier mapping saved to docs/MODEL_TIERS.md. Each skill declares its required effort + reasoning in its frontmatter — your runtime should consult this mapping to select the right model. Re-run `calibrate` any time your available models change."
