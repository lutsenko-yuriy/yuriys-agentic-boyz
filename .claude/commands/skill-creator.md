Run via Bash: `python3 scripts/skill_router.py skills/configure/skill-creator/SKILL.md --args '$ARGUMENTS'`
If the script exits non-zero (LM Studio unavailable or model not loaded), fall back to reading `skills/configure/skill-creator/SKILL.md` and executing it yourself.

$ARGUMENTS