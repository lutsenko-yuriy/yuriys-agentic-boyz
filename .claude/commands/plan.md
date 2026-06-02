Route this invocation to a subagent. **Do not execute the skill yourself.**

**Skill:** plan
**Tier:** THOROUGH + ARCHITECTURAL
**Model alias:** opus

Steps:
1. Read `skills/design/plan/SKILL.md` using the Read tool.
2. Spawn an Agent with:
   - `model`: `"opus"`
   - `prompt`: full content of the skill file, followed by the arguments below.

**Arguments:**
$ARGUMENTS
