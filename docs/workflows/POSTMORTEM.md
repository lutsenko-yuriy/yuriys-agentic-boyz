# Postmortem Workflow

Use this workflow for post-fix root-cause investigation tickets — reconstructing *when* and
*why* a shipped bug was introduced, after `docs/workflows/TROUBLESHOOT.md` has already produced
the fix. For diagnosing and fixing a live bug, use `TROUBLESHOOT.md` instead; for new-idea
research, use `docs/workflows/RESEARCH.md`.

@skills/shared/decision-guidelines.md

## Steps

1. **Title and scope the ticket.** Prefix the title `Postmortem: <what regressed>` so investigation
   tickets are recognizable in the backlog at a glance. Investigation only — no production code
   changes; a newly-discovered bug found along the way gets its own ticket per
   `docs/workflows/TROUBLESHOOT.md`.
2. **Set a due date.** These tickets carry no urgency pressure and are easy to let sit for weeks.
   Set a due date ~1-2 weeks out at creation. If a postmortem ticket's due date has passed by the
   time `summarize` next reviews the backlog, flag it explicitly and ask whether to proceed now or
   drop it — see `skills/manage/summarize/SKILL.md`.
3. **Find the origin.** `git log -S`/`git blame`/`git bisect` on the regressed behavior. Don't
   stop at the first commit that merely touches the file — trace past refactors/moves to the
   commit that actually introduced the behavior.
4. **Reconstruct the reasoning.** Read that commit's message, PR/MR description, and tests — was
   the behavior deliberate at the time, or an unintended side effect of unrelated work?
5. **Assess the detection gap.** Why didn't review or tests catch it? A test that encodes the
   bug as its expected, passing behavior is a real gap — but check whether there's more to it,
   e.g. two individually-reasonable decisions in separate PRs/MRs whose *interaction* nothing tested.
6. **Capture findings** via `/note {{ISSUE_PREFIX}}-XX: <finding>` as they emerge, same as
   `docs/workflows/RESEARCH.md`.
7. **Open a PR/MR for the findings note as soon as it's substantive**, even though there's no code
   — unlike `docs/workflows/RESEARCH.md`'s default of no PR/MR beyond the debrief commit, a
   postmortem's findings are worth reviewing in a readable diff view before the ticket closes.
   Push follow-up commits (more findings, the debrief) onto the same branch/PR.
8. **Propose a concrete prevention change**, if one exists — sized to the actual gap found, not
   a blanket policy.
9. **Debrief and close** with `/debrief {{ISSUE_PREFIX}}-XX` when all investigation questions are answered.
