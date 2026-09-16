# Git/GitHub CLI safety

Comment and commit bodies routinely contain backticks (code identifiers). Never build
them via inline shell interpolation (`git commit -m "$(cat <<'EOF' ... EOF)"`,
`--field body="$(cat file)"` with backticks in the file). Both mangle on backticks.

Always write the body to a temp file first, then pass it by reference:
- `git commit -F <file>`
- `gh pr comment <n> --body-file <file>` / `gh pr create --body-file <file>`
- `gh api ... --field body=@<file>` (the `@` prefix reads from a file)
