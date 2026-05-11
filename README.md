# Claude Multi-Agent Project Template

A GitHub template repository that bootstraps a **Claude Code multi-skill workflow** with your choice of project management tool (Linear, Jira, GitHub Issues, etc.) and Git host (GitHub, GitLab, Bitbucket) for any new project in minutes.

## What's included

| File | Purpose |
|---|---|
| `.claude/skills/setup-model-tiers.md` | One-time setup: propose and approve the model → tier mapping using THOROUGH + ARCHITECTURAL reasoning |
| `.claude/skills/product-owner-backlog.md` | Session-start: present the PM backlog and ask "What goes into the next release?" |
| `.claude/skills/product-owner-merge.md` | Post-merge: close PM issues, update CHANGELOG, BACKLOG, version, and merge |
| `.claude/skills/tech-lead-plan.md` | Produce a structured implementation plan from PM issues before coding starts |
| `.claude/skills/tech-lead-review.md` | Architectural review of a PR/MR after the Developer opens it |
| `.claude/skills/developer.md` | Implement a Tech Lead work unit following TDD; open a PR/MR |
| `.claude/skills/code-reviewer.md` | Runtime, migration, and launch-risk review of a PR/MR |
| `CLAUDE.md` | Orchestrator file: session start, workflow steps, branch naming, review chain |
| `docs/PRODUCT_SPEC.md` | Blank product spec template |
| `docs/ARCHITECTURE.md` | Blank architecture doc template |
| `docs/BACKLOG.md` | Generated from your PM tool — do not edit by hand |
| `docs/CHANGELOG.md` | Maintained by the product-owner-merge skill after each merged PR/MR |
| `docs/VERSIONING.md` | Versioning strategy template |
| `docs/MODEL_TIERS.md` | Effort Tier + Reasoning Depth vocabulary; maps each skill to a model tier |
| `setup.sh` | Interactive setup script — substitutes `{{PLACEHOLDERS}}` throughout |

## Skill roles

```
Session start
  └─▶ product-owner-backlog — presents backlog, asks "what goes into the next release?"

Large feature work
  └─▶ tech-lead-plan — produces implementation plan, waits for approval
         └─▶ developer — implements (TDD), opens PR/MR
                └─▶ tech-lead-review + code-reviewer — parallel review (architectural + runtime)
                       └─▶ product-owner-merge — closes issues, regenerates docs, merges PR/MR
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
- Experiment tracking tool

All `{{PLACEHOLDER}}` values across every file are substituted in one step.

### 4. Finish manual setup

After `setup.sh`:

1. **`CLAUDE.md` — Common Commands**: fill in the test, lint, build, and install commands for your stack.
2. **`docs/PRODUCT_SPEC.md`**: describe your features from the user's perspective.
3. **`docs/ARCHITECTURE.md`**: add your directory tree and layer rules.
4. **`CLAUDE.local.md`** *(not committed)*: add local binary paths, PM tool auth notes, and any machine-specific config.

### 5. Map your models to tiers

Open Claude Code. Invoke the `setup-model-tiers` skill:

```
Invoke the setup-model-tiers skill
```

This skill uses **THOROUGH + ARCHITECTURAL** reasoning (your most capable model) to read the model list you provided, characterise each model's strengths, and propose which model should handle each Effort Tier + Reasoning Depth combination. Review and approve the proposal — it gets written into `docs/MODEL_TIERS.md` as the **Active mapping**.

Re-run this skill any time your available models change.

### 6. Authenticate your PM tool MCP (if applicable)

If your PM tool has an MCP server (e.g. Linear), open Claude Code in your project directory and run `/mcp` to authenticate. See `CLAUDE.local.md` for notes.

### 7. Start your first session

Open Claude Code. The `CLAUDE.md` session-start instructions will automatically invoke the `product-owner-backlog` skill, which will present an empty backlog and ask: **"What goes into the first release?"**

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
- **Tool-agnostic by design** — the skills describe what to do (fetch issues, open a PR/MR, post a comment) with multi-tool examples. The specific commands depend on your configured PM tool and Git host CLI.
