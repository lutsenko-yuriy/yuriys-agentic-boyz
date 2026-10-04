# Orientation

One screen, every line taken from a file in the repo (no invention), each with its source. Respect the active communication style. End with one optional Q&A turn.

1. **Project:** name and description from `skill_router.toml` `[project]`, plus a 2-3 line gist of `docs/PRODUCT_SPEC.md`.
2. **Stack:** languages, platforms and key libraries from `docs/TECH_STACK.md`, one line each.
3. **Architecture:** the `AGENTS.md` summary plus the top-level tree from `docs/ARCHITECTURE.md` (at most 10 lines).
4. **Core glossary:** up to 8 terms from `docs/GLOSSARY.md`; if it is empty say "empty, grows via /brief".
5. **Workflows:** the lifecycle brief, analyze, plan, draft-scenarios, implement, review and audit, debrief, ship; which `docs/workflows/*.md` applies when; the ticket states.
6. **Conventions:** issue prefix, PM tool (`[providers].pm`) and note path `docs/knowledge/notes/<PREFIX>-N.md`; branch naming and CHANGELOG tags; the CODE_STYLE Base standard and formatter commands; the headline bullets of `docs/CONSTRAINTS.md`; `/style`, and `CLAUDE.local.md` for per-machine settings.
7. **Machine readiness:** the `probe` results, PM MCP auth status (`/mcp`), and a `/calibrate` hint if `docs/MODEL_TIERS.md` has no active mapping.

Then offer to run `/summarize`.
