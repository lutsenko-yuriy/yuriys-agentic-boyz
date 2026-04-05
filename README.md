# Claude Multi-Agent Project Template

A GitHub template repository that bootstraps a **Claude Code multi-agent workflow** with [Linear](https://linear.app) for any new project in minutes.

## What's included

| File | Purpose |
|---|---|
| `.claude/agents/product-owner.md` | Presents the Linear backlog at session start; closes issues and regenerates docs after PR merge |
| `.claude/agents/tech-lead.md` | Produces implementation plans from Linear issues; reviews PRs architecturally |
| `.claude/agents/developer.md` | Implements work units following strict TDD; opens PRs linked to Linear |
| `.claude/agents/code-reviewer.md` | Reviews PRs for runtime risks, migration issues, and platform-specific edge cases |
| `.mcp.json` | Linear MCP server config (universal — no changes needed) |
| `CLAUDE.md` | Orchestrator file: session start, workflow steps, branch naming, review chain |
| `docs/PRODUCT_SPEC.md` | Blank product spec template |
| `docs/ARCHITECTURE.md` | Blank architecture doc template |
| `docs/BACKLOG.md` | Generated from Linear — do not edit by hand |
| `docs/CHANGELOG.md` | Maintained by the Product Owner agent after each merged PR |
| `docs/VERSIONING.md` | Versioning strategy template |
| `CLAUDE.local.md` | Local machine settings (not committed) |
| `setup.sh` | Interactive setup script — substitutes `{{PLACEHOLDERS}}` throughout |

## Agent roles

```
Session start
  └─▶ Product Owner — presents backlog, asks "what goes into the next release?"

Large feature work
  └─▶ Tech Lead — produces implementation plan, waits for approval
         └─▶ Developer — implements (TDD), opens PR
                └─▶ Tech Lead + Code Reviewer — parallel PR review
                       └─▶ Product Owner — closes issues, regenerates docs, merges PR
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
- Tech stack
- Architecture summary
- Linear workspace name, team ID, project ID, and issue prefix

All `{{PLACEHOLDER}}` values across every file are substituted in one step.

### 4. Finish manual setup

After `setup.sh`:

1. **`CLAUDE.md` — Common Commands**: fill in the test, lint, build, and install commands for your stack.
2. **`docs/PRODUCT_SPEC.md`**: describe your features from the user's perspective.
3. **`docs/ARCHITECTURE.md`**: add your directory tree and layer rules.
4. **`CLAUDE.local.md`** *(not committed)*: add local binary paths (e.g. paths to runtimes not on `$PATH`).

### 5. Authenticate Linear MCP

Open Claude Code in your project directory. On first use, run `/mcp` to trigger the OAuth flow for Linear.

### 6. Start your first session

Open Claude Code. The `CLAUDE.md` session-start instructions will automatically invoke the Product Owner agent, which will present an empty backlog and ask: **"What goes into the next release?"**

## Placeholders reference

| Placeholder | Example value |
|---|---|
| `{{PROJECT_NAME}}` | `My App` |
| `{{PROJECT_DESCRIPTION}}` | `A task manager for remote teams` |
| `{{STACK}}` | `Flutter/Dart` |
| `{{ARCHITECTURE_SUMMARY}}` | `Vertical-slice with Riverpod + sqflite` |
| `{{CODE_STYLE}}` | `Flutter style guide` |
| `{{LINEAR_WORKSPACE_NAME}}` | `My Workspace` |
| `{{LINEAR_TEAM_ID}}` | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `{{LINEAR_PROJECT_ID}}` | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `{{LINEAR_ISSUE_PREFIX}}` | `APP` |
| `{{LINEAR_PROJECT_URL}}` | `https://linear.app/my-workspace/project/...` |

## Notes

- **`.claude/agents/` is committed** — that's intentional. The agents are part of the project workflow. If you want agents to be local-only, add `.claude/*` / `!.claude/agents/` to your `.gitignore` after setup.
- **Linear MCP auth is per-developer** — each team member authenticates via OAuth independently. No secrets are stored in the repo.
- **`CLAUDE.local.md` is gitignored** — put machine-specific paths and personal notes there.
