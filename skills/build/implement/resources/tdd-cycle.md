**Red — write failing tests first.**

- Mirror source structure under the test directory. Run the test command (see `CLAUDE.md` → "Common Commands") to confirm failure before writing any implementation code.
- If `draft-scenarios` stubs already exist in the integration test directory, use those as the red target — do not write separate unit tests for the same behaviour. Make the stubs green.

**Green — implement the minimum code to pass.**

- Write only what is needed. Follow `docs/ARCHITECTURE.md` for structure and `CLAUDE.md` for code style.
- Never import across feature or layer boundaries in ways that violate the architecture.

**Refactor — clean up without breaking tests.**

Remove duplication, improve naming, simplify logic. Re-run the test command after every step.

**Commit — after each red→green→refactor cycle.**

When one logical unit is complete (tests pass, refactor done), commit immediately before starting the next:

```bash
git commit -m "$(cat <<'EOF'
<type>: <what this logical unit does>

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

Types: `feat` (new behaviour), `fix` (bug-fix cycle), `refactor` (restructure-only), `test` (test-only change).

Repeat the full red→green→refactor→commit cycle for each logical unit. The PR accumulates one commit per cycle — reviewable commit-by-commit on the Git host.
