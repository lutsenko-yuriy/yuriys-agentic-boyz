# Project Config

Read this file to resolve all project-specific constants referenced in skill instructions.
Project identity (name, issue prefix, git host, PM tool, test/version settings) lives in `skill_router.toml`
(`[project]`, `[providers]`, `[tools]`, `[release]`). Skills stay unchanged.

## Tech stack

Languages, frameworks, platforms and tooling: `docs/TECH_STACK.md`.

## Tools

What the project uses for each role, recorded by `/onboard` in `skill_router.toml` `[tools]`: a tool name, or `none` (no such tool yet; a deliberate answer, not a gap). One tool may fill several roles.

| Key | Role |
|---|---|
| `[tools].analytics` | Analytics: where the events in `docs/ANALYTICS_EVENTS.md` are sent |
| `[tools].logging` | Logging and crash reporting |
| `[tools].feature_flags` | Feature flags: kill-switches and remote config; also the experiment tool |

A missing `[tools]` table (onboarded before these were recorded) or an empty value (e.g. `""` from a merged template `skill_router.toml`) means the same: assume a tool exists (the previous behaviour). Consumers act only on `none`; any other state proceeds as if the tool exists.

## Release

How `/prepare-release` publishes a release, recorded by `/onboard` in `skill_router.toml` `[release]`: a value, or `none`. The release flow and the term "version gate" are defined in `docs/VERSIONING.md` (Release flow).

| Key | Value |
|---|---|
| `[release].job` | One shell command that starts the release job after the `vX.Y.Z` tag is pushed, with `{version}` (`X.Y.Z`) and `{tag}` (`vX.Y.Z`) substituted, e.g. `gh workflow run release.yml -f tag={tag}`. `none`: no job; publishing is up to the user. |
| `[release].version_gates` | Where the project records the minimum app version each feature flag needs, as a file and symbol, e.g. `lib/config/flags.dart (Flags.releaseVersions)`. `none`: the project keeps no gates. |

A missing `[release]` table (onboarded before these were recorded) or an empty value means "not recorded", which differs from `[tools]`: there is no command to assume. `/prepare-release` then stops after the tag and says publishing is up to the user, and when flagged lines are selected it asks for the gate location or an explicit "proceed without gates". `version_gates = none` with flagged lines selected gets the same risk warning in the release summary.

## Repositories

`skill_router.toml` `[project].code_repo_dir` is empty in most projects: one repo holds everything, and the two-repo notes in skills do not apply. Skip them.

When it is set (a path relative to this repo or starting with `~`, e.g. `../app`), this repo is the **tracking repo** and the session runs here, launched with `claude --add-dir <code_repo_dir>`. The code lives in the **code repo**:

| Artifact | Repo |
|---|---|
| Code, tests, skill and workflow files | code repo |
| Issues (PM), `docs/knowledge/notes/`, CHANGELOG, BACKLOG, ADRs | tracking repo |

- Run git in the code repo as `git -C <code_repo_dir>`, and `gh` as `gh ... -R <code-slug>`, where `<code-slug>` is `gh repo view --json nameWithOwner -q .nameWithOwner` run in that directory. Tests, formatter and linter are the code repo's own commands, run there.
- Issue IDs, the prefix and branch names are the tracking repo's: `feature/{{ISSUE_PREFIX}}-XX-<desc>` in both repos.
- Each ticket has two PRs. The **code PR** says `Part of <tracking-slug>#N`, never `Closes`: `/ship` closes the issue. The **tracking PR**, on the same branch name in the tracking repo, carries the CHANGELOG line, BACKLOG and notes.
- The CHANGELOG cites the code PR as `(PR <code-slug>#N)`.
- When the code repo is the template these skills come from, the session runs the tracking repo's synced copy of each skill, not the one being edited.

## Project management

@skills/shared/pm-tool-mapping.md

## Documentation paths

| Document | Path |
|---|---|
| Product spec | `docs/PRODUCT_SPEC.md` |
| Glossary | `docs/GLOSSARY.md` |
| Backlog | `docs/BACKLOG.md` |
| Changelog | `docs/CHANGELOG.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Agent workflow | `AGENTS.md` |
| Knowledge base | `docs/knowledge/notes/` (one `{{ISSUE_PREFIX}}-XX.md` file per ticket) |

## Testing

| Setting | Value |
|---|---|
| Integration test directory | `{{INTEGRATION_TEST_DIR}}` (e.g. `integration_test/`, `e2e/`) |
| Test harness file | `{{TEST_HARNESS_FILE}}` (e.g. `integration_test/harness.dart`) |
| Harness class / entry point | `{{TEST_HARNESS_CLASS}}` (e.g. `AppHarness`) |
| Unit / integration test command | `{{TEST_COMMAND}}` (e.g. `flutter test`, `npm test`, `pytest`) |

## Version management

| Setting | Value |
|---|---|
| Version file | `{{VERSION_FILE}}` (e.g. `pubspec.yaml`, `package.json`) |
| Version field | `{{VERSION_FIELD}}` (e.g. `version: X.Y.Z`) |
| Who bumps it | Only `/prepare-release`, with the version the user confirms; CI manages build numbers — never touch them |

## In QA path patterns

A merged PR moves to **In QA** (not Done directly) if it touches any of:

- `{{IN_QA_PATHS}}` — list the directories or file patterns that require human QA sign-off

Move straight to **Done** if the PR touches only: pure logic with no runtime platform dependency, documentation, CI config, or pure refactors where automated tests fully own correctness. When in doubt, use **In QA**.
