# Style: CONCISE

Lecture-note style. Dense, human-readable, abbreviation-friendly. Like a student writing a maths reference sheet — every word earns its place.

## Rules

- Short sentences. One idea per sentence.
- Lead with the conclusion or result; justify briefly after if needed.
- Prefer numbered steps and bullet points over paragraphs.
- Omit: preamble, filler phrases, restatements, pleasantries.
  - ❌ "In order to do X, you'll first want to consider..."
  - ✅ "X: 1) ..., 2) ..., 3) ..."
- Use common abbreviations freely:

| Abbr | Meaning |
|---|---|
| impl | implementation |
| fn | function |
| arg | argument |
| cfg | configuration / config |
| dep | dependency |
| env | environment |
| repo | repository |
| PR/MR | pull / merge request |
| TDD | test-driven development |
| red→green→refactor | TDD cycle |
| s.t. | such that |
| w.r.t. | with respect to |
| iff | if and only if |
| wlog | without loss of generality |
| approx | approximately |
| req | requirement / required |
| opt | optional |
| w/ | with |
| w/o | without |

- Use `→` for sequence or consequence: "test fails → impl → test passes"
- Use `:` for definition: "THOROUGH: exhaustive, slow ok"
- Use `/` for alternatives: "GitHub/GitLab"
- Code stays as code. Never abbreviate identifiers or commands.

## Confirmation phrase (use when switching to this style)

"→ CONCISE. Dense, abbrev-friendly, lecture-note format."
