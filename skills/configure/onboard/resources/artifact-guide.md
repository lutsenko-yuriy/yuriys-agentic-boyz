# Artifact guide

How `/onboard` infers the stack and fills `docs/TECH_STACK.md`, `docs/CODE_STYLE.md` and `docs/CONSTRAINTS.md`. Read-only reference.

## Inferring the stack

Read manifests and config; never run a toolchain to ask its version. Cite the source file in the Version column.

| Evidence (read it) | Tells you |
|---|---|
| `pubspec.yaml` (`environment:`, `dependencies:`) | Dart, Flutter, libraries |
| `package.json` (`engines`, `dependencies`), `tsconfig.json` | Node, TypeScript, libraries |
| `build.gradle.kts`, `build.gradle`, `settings.gradle*`, `gradle/wrapper/gradle-wrapper.properties` | Kotlin or Java, JVM target, Gradle version, libraries |
| `pyproject.toml`, `requirements*.txt`, `.python-version` | Python, version, libraries |
| `Cargo.toml`, `go.mod`, `Gemfile` | Rust, Go, Ruby |
| `scripts/`, `.claude/hooks/` | Python and Shell used for tooling; list them as languages too |
| `android/`, `ios/`, `macos/`, `web/` directories, `AndroidManifest.xml` | Target platforms |
| `.github/workflows/*.yml` | CI service, test and build commands |
| `Makefile`, `package.json` scripts, README "Common commands" | Test, lint, build and install commands |

List every language that has source in the repo, including tooling languages such as Python or Shell under `scripts/`. Show the inferred table to the user and ask for corrections before writing.

## Style guides and enforcers

Name the published guide for each language with a link. List an enforcer (formatter, linter) only when its config or CI step exists in the repo; otherwise state "no enforcer configured".

| Language | Style guide | Enforcer, only if configured |
|---|---|---|
| Dart | Effective Dart, Flutter style guide | `dart format`, `flutter analyze` (`analysis_options.yaml`) |
| TypeScript | TypeScript Handbook conventions | ESLint (`.eslintrc*`, `eslint.config.*`), Prettier (`.prettierrc*`) |
| Kotlin | Kotlin coding conventions | ktlint or detekt (Gradle plugin or config file) |
| Java | Google Java Style Guide | Checkstyle or google-java-format (config file) |
| Python | PEP 8 | ruff, black, flake8 (`pyproject.toml`, `ruff.toml`, `.flake8`) |
| Shell | Google Shell Style Guide | shellcheck (CI step or `.shellcheckrc`) |

## Filling the files

- `docs/TECH_STACK.md`: keep the section and table shapes of the template. The first column of the Languages table is the language name alone (`Dart`, not `Dart 3`); put the version in the second column.
- `docs/CODE_STYLE.md`: under `## Base standard` put one line per TECH_STACK language, starting with the exact language name, then the guide link. Formatting, Linting, Naming and structure, and Comments come from the repo's configs and conventions; a section is dropped only by giving it a real statement or "none".
- `docs/CONSTRAINTS.md`: ask the user for team and capacity, stage, environment, budget and compliance. Record answers as given; "none known" is a valid answer.
- In all three: strip the `<!-- yab:template -->` line, every `<...>` token and the guidance comments. `check` rejects what is left over.
