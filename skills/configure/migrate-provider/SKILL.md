---
name: migrate-provider
effort: RAPID
reasoning: TACTICAL
needs_session_tools: true
output_style: CONCISE
description: Switch a tool role (pm, vcs, files) to a different provider implementation. Reads skill_router.toml, validates the target provider exists, updates [providers], and prints env var instructions. Skill frontmatter does not need to change — roles are stable across tool switches.
---

## Overview

The skill router maps **role names** (`pm`, `vcs`, `files`) to concrete provider implementations
in `skill_router.toml`. Switching tools means:
1. Editing one TOML line (e.g. `pm = "jira"` → `pm = "linear"`)
2. Setting the new provider's env var
3. Adding a `[<provider>]` config table if the new provider needs project-specific settings

Skill `.md` files reference roles, not tool names — they never need to change when you migrate.

Data migration (exporting issues/tickets from the old tool into the new one) is **out of scope**
for this skill — use each tool's official export/import flow.

---

## Steps

### 1. Read current config

Read `skill_router.toml` and display the current `[providers]` mapping.

### 2. Ask what to migrate

Ask the user:
- **Which role?** (`pm`, `vcs`, or another role listed in `[providers]`)
- **Which provider?** List what is already implemented under `scripts/skill_router/providers/`

### 3. Validate the target provider exists

Check that `scripts/skill_router/providers/<target>/provider.py` exists and the class is
registered in `scripts/skill_router/providers/__init__.py:PROVIDER_REGISTRY`.

If not, inform the user:
> Provider `<name>` is not yet implemented. To add it:
> 1. Create `scripts/skill_router/providers/<name>/provider.py` with a class that implements `ToolProvider` (and `PMToolProvider` if it's a `pm` role).
> 2. Register it in `scripts/skill_router/providers/__init__.py`.
> Then re-invoke this skill.

### 4. Update `skill_router.toml`

Edit the line `<role> = "<old_provider>"` → `<role> = "<new_provider>"` in `[providers]`.

If the new provider needs project-specific settings, add a `[<new_provider>]` table
and prompt the user for the values (e.g. `project_id` for Linear, `project_key` for Jira).

### 5. Print env var instructions

Look up the `from_config` classmethod of the new provider to determine which env vars it reads
(e.g. `LINEAR_API_KEY`, `JIRA_API_TOKEN`). Print the exact export command:

```
export <ENV_VAR>=<your_token>
```

Remind the user to add this to `CLAUDE.local.md` (not committed) so future sessions pick it up.

### 6. Confirm

Show a summary:
- Role migrated: `<role>` → `<new_provider>`
- TOML updated: `skill_router.toml`
- Env var needed: `<ENV_VAR>`
- Next step: restart the session so the new provider is active
