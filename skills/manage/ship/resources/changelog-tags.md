| Tag | When to use | Triggers build? | Appears in release notes? |
|---|---|---|---|
| `- [user] <description>` | User-visible product change | Yes | Yes — tag stripped |
| `- [app] <description>` | Code change, not user-visible | Yes | No |
| `- [test] <description>` | Test-only changes — no production code | No | No |
| `- [meta] <description>` | Skills / agent / workflow change | No | No |
| `- [ci] <description>` | CI/CD process change | No | No |
| `- [non-user] <detail>` | Supplementary bullet within a classified entry | — | No |

Rules:
- Every `## [X.Y.Z]` entry must carry at least one of: `[user]`, `[app]`, `[test]`, `[meta]`, `[ci]`.
- `[non-user]` is supplementary only — it does **not** satisfy the classification requirement on its own.
- `[user]` descriptions must be readable by end users with no technical background: no class names, file paths, internal terms, or jargon.
- Place `[user]` lines before technical detail lines within the same section.
- The tag list may grow; each new tag must declare its build and release-note behaviour.
