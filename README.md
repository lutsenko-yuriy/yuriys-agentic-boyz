# Multi-Agent Project Template

A GitHub template repository that bootstraps a **multi-skill AI workflow** with your choice of project management tool (Linear, Jira, GitHub Issues, etc.) and Git host (GitHub, GitLab, Bitbucket) for any new project in minutes.

## What's included

| File | Purpose |
|---|---|
| `skills/configure/calibrate/SKILL.md` | One-time setup: propose and approve the model → tier mapping |
| `skills/configure/style/SKILL.md` | Switch communication style: DETAILED, CONCISE, or SCHEMATIC |
| `skills/manage/summarize/SKILL.md` | Session-start: fetch and display the backlog |
| `skills/manage/ship/SKILL.md` | Post-merge housekeeping: close issues, update docs, bump version, merge |
| `skills/design/analyze/SKILL.md` | Analytics planning: identify events and screen views for a feature |
| `skills/design/plan/SKILL.md` | Implementation planning: structured plan from a PM issue |
| `skills/build/implement/SKILL.md` | TDD implementation and PR/MR |
| `skills/verify/review/SKILL.md` | Architectural PR/MR review |
| `skills/verify/audit/SKILL.md` | Runtime and migration PR/MR review |
| `styles/DETAILED.md` | Style def: full prose, default |
| `styles/CONCISE.md` | Style def: lecture-note shorthand, abbreviation-friendly |
| `styles/SCHEMATIC.md` | Style def: TeX-math + Haskell notation |
| `CLAUDE.md` | Orchestrator file: session start, workflow steps, branch naming, review chain |
| `docs/PRODUCT_SPEC.md` | Blank product spec template |
| `docs/ARCHITECTURE.md` | Blank architecture doc template |
| `docs/BACKLOG.md` | Generated from your PM tool — do not edit by hand |
| `docs/CHANGELOG.md` | Maintained by the `ship` skill after each merged PR/MR |
| `docs/VERSIONING.md` | Versioning strategy template |
| `docs/MODEL_TIERS.md` | Effort Tier + Reasoning Depth vocabulary; active model → tier mapping |
| `setup.sh` | Interactive setup script — substitutes `{{PLACEHOLDERS}}` throughout |

## Skill workflow

```
Session start
  └─▶ summarize — presents backlog, asks "what goes into the next release?"

User-facing feature
  └─▶ analyze — plans analytics events and screen views, waits for approval
        └─▶ plan — produces implementation plan, waits for approval
               └─▶ implement — TDD, opens PR/MR
                      └─▶ review + audit — parallel review (architectural + runtime)
                             └─▶ ship — closes issues, regenerates docs, merges PR/MR
```

## Quick start

### 1. Create a new repo from this template

Click **"Use this template"** → **"Create a new repository"** on GitHub.

### 2. Clone your new repo

```bash
git clone https://github.com/<you>/<your-project>.git
cd <your-project>
```

### 3. Run the setup script

```bash
chmod +x setup.sh
./setup.sh
```

The script will prompt for:
- Project name and description
- Tech stack and architecture summary
- PM tool name (Linear, Jira, GitHub Issues, etc.) and issue prefix
- Git host (GitHub, GitLab, Bitbucket)
- Available AI models (comma-separated — used by `calibrate`)
- Experiment tracking tool
- AI commit trailer and PR/MR credit lines

All `{{PLACEHOLDER}}` values across every file are substituted in one step.

### 4. Finish manual setup

After `setup.sh`:

1. **`CLAUDE.md` — Common Commands**: fill in the test, lint, build, and install commands for your stack.
2. **`docs/PRODUCT_SPEC.md`**: describe your features from the user's perspective.
3. **`docs/ARCHITECTURE.md`**: add your directory tree and layer rules.
4. **`CLAUDE.local.md`** *(not committed)*: add local binary paths, PM tool auth notes, and any machine-specific config.

### 5. Map your models to tiers

Invoke the `calibrate` skill:

```
Invoke the calibrate skill
```

This skill uses **THOROUGH + ARCHITECTURAL** reasoning (your most capable model) to read the model list you provided, characterise each model's strengths, and propose which model should handle each Effort Tier + Reasoning Depth combination. Review and approve the proposal — it gets written into `docs/MODEL_TIERS.md` as the **Active mapping**.

Re-run `calibrate` any time your available models change.

### 6. Authenticate your PM tool MCP (if applicable)

If your PM tool has an MCP server (e.g. Linear), open Claude Code in your project directory and run `/mcp` to authenticate. See `CLAUDE.local.md` for notes.

### 7. Start your first session

The `CLAUDE.md` session-start instructions will automatically invoke the `summarize` skill, which will present an empty backlog and ask: **"What goes into the first release?"**

## Placeholders reference

| Placeholder | Example value |
|---|---|
| `{{PROJECT_NAME}}` | `My App` |
| `{{PROJECT_DESCRIPTION}}` | `A task manager for remote teams` |
| `{{STACK}}` | `Flutter/Dart` |
| `{{ARCHITECTURE_SUMMARY}}` | `Vertical-slice with Riverpod + sqflite` |
| `{{CODE_STYLE}}` | `Flutter style guide` |
| `{{PM_TOOL}}` | `Linear` |
| `{{ISSUE_PREFIX}}` | `APP` |
| `{{PM_PROJECT_URL}}` | `https://linear.app/my-workspace/project/...` |
| `{{GIT_HOST}}` | `GitHub` |
| `{{EXPERIMENT_TOOL}}` | `Firebase A/B Testing` |
| `{{AVAILABLE_MODELS}}` | `gpt-4o, gpt-4o-mini` |
| `{{AI_COMMIT_TRAILER}}` | `Co-Authored-By: AI Assistant <ai@example.com>` |
| `{{AI_TOOL_CREDIT}}` | `🤖 Generated with Claude Code` |

## Notes

- **`.claude/skills/` is committed** — skills are part of the project workflow. If you want them local-only, add `.claude/skills/` to `.gitignore` after setup.
- **PM tool auth is per-developer** — each team member authenticates independently via their tool's MCP or CLI. No secrets are stored in the repo.
- **`CLAUDE.local.md` is gitignored** — put machine-specific paths and personal notes there.
- **Tool-agnostic by design** — skills describe what to do with multi-tool example tables (Linear/Jira/GitHub/GitLab, GitHub/GitLab/Bitbucket). Specific commands depend on your configured tools.
- **Model-agnostic by design** — skills declare `effort` and `reasoning` tiers instead of model names. The `calibrate` skill maps your available models to those tiers once, and the active mapping lives in `docs/MODEL_TIERS.md`.
- **Communication styles** — the `style` skill switches between DETAILED (full prose), CONCISE (lecture-note shorthand), and SCHEMATIC (TeX-like notation). Active style persists across sessions via `CLAUDE.local.md`.
