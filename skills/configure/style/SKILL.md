---
name: style
effort: RAPID
reasoning: MECHANICAL
description: Switch the active communication style for this session. Three styles available — DETAILED (full prose, default), CONCISE (lecture-note shorthand, abbreviation-friendly), SCHEMATIC (minimal words, TeX-like symbols). Invoke as: "Invoke the style skill with CONCISE" or "/style SCHEMATIC". Persists the choice to CLAUDE.local.md so the next session can restore it.
---

## Steps

### 1. Read the requested style

The style name is passed as the argument: `DETAILED`, `CONCISE`, or `SCHEMATIC`.

If no argument is given or the name is unrecognised, list the available styles with their recommended use cases and ask the user to choose:

```
Available styles:
- DETAILED   — full prose, complete explanations (default)
               Best for: long-form docs, specs, ADRs, onboarding material
- CONCISE    — lecture-note shorthand, abbreviation-friendly
               Best for: live chat, PR reviews, code comments, day-to-day session replies
- SCHEMATIC  — TeX-math + Haskell notation, zero prose
               Best for: agent-to-agent output, workflow/pipeline specs, type-level reasoning

Which style?
```

### 2. Load the style rules

Read `styles/<STYLE>.md` in full and internalise the rules. Apply them immediately — every response from this point forward must conform to the loaded style.

### 3. Persist the active style

Open `CLAUDE.local.md` (create it if absent) and update or add the active style line:

```
## Active communication style
CONCISE
```

Replace any existing `## Active communication style` section. Do not touch any other content in `CLAUDE.local.md`.

### 4. Confirm

Respond with the confirmation phrase defined at the bottom of the loaded style file, written *in that style*.

---

## Style resolution order

1. **Active session style** — if `CLAUDE.local.md` contains `## Active communication style`, load it and apply it to all output, overriding every skill's own default.
2. **Skill default** — if no session style is set, each skill uses the `output_style` declared in its own frontmatter.

There is no global fallback. If neither is set, the skill chooses based on its own `output_style`.

## Notes for session start

At session start, before invoking `summarize`, check `CLAUDE.local.md` for an `## Active communication style` section. If present, silently load that style file — it overrides all skill defaults for this session. If absent, each skill will use its own `output_style`.
