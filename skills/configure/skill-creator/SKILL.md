---
name: skill-creator
effort: FOCUSED
reasoning: ARCHITECTURAL
needs_session_tools: true
output_style: CONCISE
description: Two modes. No-arg (create): guided wizard → new skill with SKILL.md + resources + command stub + AGENTS.md entry. With-path (refactor): extracts reference material from an existing skill into sibling resource files, replacing inline content with @path references. Pass "all" to refactor every skill in AGENTS.md sequentially.
---

## Active tier mapping

@docs/MODEL_TIERS.md

---

## Modes

Determine mode from the argument:
- **No argument** → Create mode.
- **`skills/<path>`** → Refactor mode: one skill.
- **`all`** → Refactor mode: all skills listed in AGENTS.md, sequentially.

---

## Create mode

### 1. Gather requirements

Ask in one message:
1. "What should this skill do? (1–3 sentences)"
2. "When is it invoked? (before implementation, post-merge, on demand, at session start, …)"
3. "Does it need session tools — file read/write, PM tool, GitHub, or Bash?"

### 2. Infer metadata

| Field | How to infer |
|---|---|
| `effort` | THOROUGH if codebase-wide; FOCUSED for scoped generation or review; RAPID for fast lookups |
| `reasoning` | ARCHITECTURAL for system-design or planning; TACTICAL for implementation; MECHANICAL for formatting |
| `needs_session_tools` | `true` if PM tool/GitHub MCP, file tools, or Bash are needed |
| Category | `configure`, `design`, `build`, `manage`, `run`, or `verify` |
| Name | Short kebab-case verb or noun matching the primary action |

Propose the inferred metadata and name. Wait for confirmation before proceeding.

### 3. Draft the skill

Produce a complete draft:
- `SKILL.md` — frontmatter + numbered steps; large reference blocks go in resource files
- `resources/<name>.md` — any templates, checklists, or decision tables (one file per topic)

Present everything and wait for approval or iteration.

### 4. Write files (after approval)

1. Write `skills/<category>/<name>/SKILL.md`
2. Write `skills/<category>/<name>/resources/<name>.md` for each resource
3. Write `.claude/commands/<name>.md` stub using the routing rules below
4. Add rows to the AGENTS.md Documentation and Slash commands tables

### 5. Report

List all files written and the `/command-name` to invoke the skill.

---

## Command stub formats

**Routing rule:** only spawn when the target model differs from the current session model.

**Script stub** (`needs_session_tools: true`, or `lm-studio` alias):
```
Run via Bash: `python3 scripts/skill_router.py skills/<path>/SKILL.md --args '$ARGUMENTS'`
If the script exits non-zero (LM Studio unavailable or model not loaded), fall back to reading `skills/<path>/SKILL.md` and executing it yourself.

$ARGUMENTS
```
For no-argument skills, omit `--args '$ARGUMENTS'` and the trailing `$ARGUMENTS` line.

**Agent routing stub** (spawning up to a more capable model — e.g. tier maps to `opus`, session is `sonnet`):
```
Route this invocation to a subagent. **Do not execute the skill yourself.**

**Skill:** <name>
**Tier:** <EFFORT> + <REASONING>
**Model alias:** <alias>

Steps:
1. Read `skills/<path>/SKILL.md` using the Read tool.
2. Spawn an Agent with:
   - `model`: `"<alias>"`
   - `prompt`: full content of the skill file, followed by the arguments below.

**Arguments:**
$ARGUMENTS
```

**Passthrough stub** (target model == session model):
```
@skills/<path>/SKILL.md

$ARGUMENTS
```

---

## Refactor mode

### 1. Read skill(s)

Read each target `SKILL.md`. For `all`, list skills from AGENTS.md first.

### 2. Classify content

**KEEP inline** — procedural (answers "what to do next?"):
- Numbered steps, concise explanations, one-line rules, short decision branches (≤ 5 lines)

**EXTRACT to `resources/`** — reference (answers "how does this work?"):
- Templates > 15 lines, lookup tables > 5 rows, multi-category checklists, sub-procedures not in the core flow

**REUSE existing docs** — no new file needed when `docs/` already has the content:
- Effort/reasoning tier map → `@docs/MODEL_TIERS.md`
- Experiment spec template → `@docs/experiments/TEMPLATE.md`

Skills < 60 lines with purely procedural content need no extraction — say so and skip.

### 3. Propose

For each skill, before writing any files:
```
## <skill-path>: <N> → ~<M> lines

Extract: `resources/<file>` — <contents> (~<lines> saved)
Reuse:   @<doc-path> (replaces <description of block>)
Keep:    <what stays inline>
```

Wait for approval.

### 4. Write

Create resource files and update SKILL.md — replace each extracted block with `@skills/<path>/resources/<file>.md` or `@<doc-path>`. Preserve frontmatter unchanged.

### 5. Report

Files created, line counts before → after for each skill.
