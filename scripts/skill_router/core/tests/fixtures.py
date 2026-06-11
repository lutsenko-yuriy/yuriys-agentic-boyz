TIERS_MD_WITH_LMSTUDIO = """\
## Active mapping

| Effort | Reasoning | Model | Claude Code alias |
|---|---|---|---|
| THOROUGH | ARCHITECTURAL | claude-opus-4-6 | `opus` |
| RAPID | MECHANICAL | qwen/qwen3-8b (MLX, 4-bit) | `lm-studio` |
| FOCUSED | ARCHITECTURAL | claude-sonnet-4-6 | `sonnet` |

---
"""

SKILL_CONTENT_PLAIN = "---\neffort: RAPID\nreasoning: MECHANICAL\n---\nDo the thing.\n"
SKILL_CONTENT_NEEDS_MCP = "---\neffort: RAPID\nreasoning: MECHANICAL\nneeds_session_tools: true\n---\nDo the thing.\n"
SKILL_CONTENT_WITH_CONTEXT = "---\neffort: RAPID\nreasoning: MECHANICAL\ncontext: linear\n---\nDo the thing.\n"
SKILL_CONTENT_WITH_TOOLS = "---\neffort: RAPID\nreasoning: MECHANICAL\ntools: linear,github\n---\nDo the thing.\n"
SKILL_CONTENT_NO_FM = "No frontmatter here."
