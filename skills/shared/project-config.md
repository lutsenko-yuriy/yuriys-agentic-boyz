# Project Config

Read this file to resolve all project-specific constants referenced in skill instructions.
When setting up the project, fill in every `{{placeholder}}`. Skills stay unchanged.

## Source control

| Setting | Value |
|---|---|
| Git host | `{{GIT_HOST}}` (e.g. GitHub, GitLab, Bitbucket) |

## Tech stack

| Layer | Technology |
|---|---|
| Framework | `{{FRAMEWORK}}` |
| State management | `{{STATE_MANAGEMENT}}` |
| Local persistence | `{{PERSISTENCE}}` |

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
| Manual vs automated | Bump version name manually; CI manages build numbers — never touch them |

## In QA path patterns

A merged PR moves to **In QA** (not Done directly) if it touches any of:

- `{{IN_QA_PATHS}}` — list the directories or file patterns that require human QA sign-off

Move straight to **Done** if the PR touches only: pure logic with no runtime platform dependency, documentation, CI config, or pure refactors where automated tests fully own correctness. When in doubt, use **In QA**.
