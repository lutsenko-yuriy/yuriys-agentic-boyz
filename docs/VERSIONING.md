# Versioning

<!-- Describe your versioning strategy. Example below — adapt to your project. -->

This project follows [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

**Major** — breaking changes (incompatible data formats, dropped platform support).
**Minor** — new features added in a backwards-compatible manner.
**Patch** — backwards-compatible bug fixes.

The next version is proposed by `/prepare-release` and confirmed by the user; no other step changes the version.

## Release flow

Merging and releasing are separate steps.

- **Merge:** `/ship` appends one line per merged PR/MR under the single `## [Unreleased]` heading at the top of `docs/CHANGELOG.md`. It never writes a numbered heading or bumps the version file. Line grammar and tags: `skills/manage/ship/resources/changelog-tags.md`; `python3 scripts/changelog/changelog.py lint docs/CHANGELOG.md` checks it, in CI too.
- **Format marker:** the lint applies only to a CHANGELOG that contains the line `<!-- changelog-format: yab-1 -->` (above the first `---`, where `/onboard` keeps it for new projects). Without it, `lint` prints a one-line notice and passes, so a CHANGELOG that predates this format keeps CI green; `/ship` and `/prepare-release` relay the notice. To opt in, rewrite the `[Unreleased]` lines in the grammar and add the marker; released sections stay as they are.
- **Semver mark:** every `[user]`/`[app]` line ends with `MAJOR`, `MINOR` or `PATCH`, the step that change needs on its own (rules above). `/ship` proposes it and the user confirms it.
- **Flags:** when the project records a feature-flag tool (`skill_router.toml` `[tools].feature_flags` is not `none`), a line also names the flags that switch its feature on and off.
- **Release:** `/prepare-release` selects the `[user]`/`[app]` lines to release, proposes the next version from the highest mark among them (MAJOR > MINOR > PATCH), moves them with the other `[Unreleased]` lines under a new `## [X.Y.Z] — YYYY-MM-DD` heading with its release notes, bumps the version file, tags `vX.Y.Z`, starts the release job if one is recorded and switches the selected flags on. Deselected lines stay in `[Unreleased]` for the next release.
- **Version gate:** the minimum app version at which a feature flag can take effect, kept in the project's own record. `/prepare-release` adds one for each selected flagged feature, so a flag switched on in the flag tool has no effect on older builds that don't contain the feature.

## CI/CD

<!-- Describe your CI/CD pipeline here. -->
