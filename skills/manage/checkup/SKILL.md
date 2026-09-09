---
name: checkup
effort: THOROUGH
reasoning: ARCHITECTURAL
needs_session_tools: true
output_style: CONCISE
description: Two-tier periodic code-quality checkup (light monthly / heavy quarterly) covering 9 non-mechanical dimensions that per-PR/MR review doesn't catch. Auto-detects which tier(s) are due via scripts/checkup/due.py, walks the tier's dimension heuristics, fixes findings inline where safe (Boy Scout Rule) or defers them to the ledger with a Fowler-quadrant classification and deadline, writes a dated run write-up, and commits. Invoke as `/checkup`, `/checkup light`, `/checkup heavy`, or `/checkup status`.
---

@skills/shared/project-config.md
@skills/shared/decision-guidelines.md

This skill audits, it doesn't ship a feature. Per [ADR-0001](../../../docs/knowledge/decisions/ADR-0001-two-tier-periodic-code-quality-checkup.md), findings are fixed inline or deferred to the ledger — never filed as individual PM tickets.

---

## Steps

### 1. Resolve which tier(s) to run

Run `python3 scripts/checkup/due.py` to get due status for both tiers.

Parse the argument:
- **No argument (auto):** run every tier `due.py` reports as `DUE`. If neither is due, print the due-status table and stop — do not run anything unless the user then names a tier explicitly.
- **`light` or `heavy`:** force that tier's run regardless of due status — the on-demand override ADR-0001 requires.
- **`status`:** print `due.py`'s table output and stop. Do not walk any dimensions.

If both tiers are due (or both are forced across the conversation), run them one at a time — light before heavy — each producing its own write-up and ledger update.

### 2. Walk the tier's dimensions

Read `resources/light-dimensions.md` (light tier, 5 dimensions) or `resources/heavy-dimensions.md` (heavy tier, 4 dimensions). Work through each dimension in order, applying its heuristic to the current codebase.

### 3. Handle each finding

Read `resources/findings-protocol.md` and follow it for every finding surfaced in step 2 — fix-inline vs. defer-with-write-up, Fowler quadrant classification, and the ledger deadline-line format.

### 4. Write the run write-up

Create `docs/knowledge/checkups/CHK-YYYY-MM-DD-<tier>.md` from `docs/knowledge/checkups/TEMPLATE.md` (today's date, the tier just run). Fill in run info and one `### <Dimension>` block per dimension that produced a finding — omit dimensions with nothing to report.

### 5. Update the ledger

In `docs/knowledge/checkups/LEDGER.md`:
- **Cadence & due status** — set the run tier's `Last run` to today's date and `Period covered` to the current period (`YYYY-MM` for light, `YYYY-Qn` for heavy — same math `due.py` uses).
- **Open findings** — append one row per deferred finding, per the findings protocol's ID/deadline format.
- **Resolved findings** — move any rows for findings this run closed out (fixed and verified, or superseded).

### 6. Commit

No PM ticket exists for a periodic checkup run (per ADR-0001), so branch and commit directly — a direct commit to `main` is blocked regardless.

**Mid-ticket** (the current branch already has an open PR/MR — check with `gh pr list --head <branch> --state open`): stay on the branch, commit, and push. The checkup output rides along with that PR/MR.

**Standalone run** (no open PR/MR): branch from `origin/main`, commit, push, open a PR/MR.
```bash
git fetch origin
git checkout -b chore/checkup-<tier>-YYYY-MM-DD origin/main
git add docs/knowledge/checkups/ <any inline-fixed files>
git commit -m "chore: <tier> checkup YYYY-MM-DD — N fixed inline, M deferred"
git push -u origin chore/checkup-<tier>-YYYY-MM-DD
gh pr create --title "chore: <tier> checkup YYYY-MM-DD" --body "<summary>"
```
No CHANGELOG entry — a checkup run is process output, not a release-relevant change (mirrors `/debrief`, which also skips the CHANGELOG). Leave the PR/MR open for the user to review and merge; do not auto-merge.

### 7. Report back

One line per tier run: dimensions walked, findings fixed inline, findings deferred (with deadlines), and the PR/MR URL (or "added to PR/MR #N" if an open one was reused).

---

## Constraints

- Never file an individual PM ticket for a finding — deferred findings go in the ledger's Open findings table only (per ADR-0001).
- An inline fix must stay within Boy Scout Rule scope — small and safe without its own test-writing cycle. Anything larger gets deferred, not force-fitted into this skill's commit.
- Do not touch `## Resolved findings` rows other than moving matching IDs in from `## Open findings` — never fabricate a resolution.
- Do not merge the PR/MR opened in step 6 — that's the user's call.
- Never modify `docs/knowledge/checkups/LEDGER.md`'s table structure — only the rows.
