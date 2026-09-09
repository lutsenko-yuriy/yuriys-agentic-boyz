---
name: research
effort: FOCUSED
reasoning: ARCHITECTURAL
needs_session_tools: true
output_style: DETAILED
description: Produce a cited, synthesized position on a claim, or a scoping-style map of a bare topic. Confirms the thesis and antithesis (or topic framing) with the user, spawns parallel search subagents per branch, and runs a single bounded synthesis pass — no iterated debate rounds. Invoke as "Invoke the research skill for <claim or topic>" or "/research <claim or topic>". Waits for approval before spending search budget and before finalising.
---

@skills/shared/project-config.md
@skills/shared/dialog-principles.md
@skills/shared/decision-guidelines.md

This skill produces a written research finding, not code. Design rationale and the full alternatives survey behind this skill's shape: `docs/knowledge/decisions/ADR-0002-dialectical-research-skill-methodology.md`.

---

## Steps

### 1. Classify the input

Read the user's input and classify it as one of:

- **Thesis** — a claim or statement to evaluate (e.g. "monthly subscriptions improve retention over one-time purchases").
- **Topic** — an open exploration with no claim to prove or disprove (e.g. "what do we know about onboarding-flow drop-off?").

If ambiguous, ask one question to disambiguate before proceeding.

### 2. Thesis mode: generate the antithesis

Skip this step entirely in topic mode — never manufacture a fake opposing claim for a bare topic.

Restate the thesis clearly, then generate the strongest reasonable antithesis — the most credible opposing position, not a straw man. Present both to the user:

> "Thesis: \<restated claim\>
> Antithesis: \<strongest opposing position\>
> Does this pair look right, or should either side be adjusted before I spend any search budget?"

Wait for explicit approval or adjustment. Do not proceed to step 3 until approved.

### 3. Spawn branch subagents in parallel

**Thesis mode — exactly two subagents**, one per branch (thesis, antithesis). This 2-way structure is deliberate: a judge choosing between two opposing positions is the specific setup with strong evidence behind it (see ADR-0002). Do not generalise to more branches for a "more thorough" result — the evidence backs two sides, not N, and iterated/multi-branch elaboration is the documented failure mode this design avoids.

**Topic mode — exactly one subagent.** There is no opposing claim to split across; forcing an artificial two-way split would invent sides that don't exist. One subagent runs a broad scoping-style search over the topic.

Spawn the subagent(s) as parallel `Agent` tool calls in a single response (not sequential turns). Each subagent's prompt must instruct it to:

- Search the general web (WebSearch/WebFetch) and, where relevant, free academic APIs (Semantic Scholar, OpenAlex, arXiv, Crossref — reachable via `curl`, no key required) for its assigned position or topic.
- **Topic mode with multiple explicit sub-questions:** run a distinct search pass per sub-question rather than one broad query and hoping it happens to surface an answer to each — breadth comes from covering each question deliberately, not from one wider net.
- Before accepting a source as snippet/metadata-only, try at least one alternate route to the primary text (the author's own site, the publisher/aggregator's own PDF link, an institutional repository copy) rather than stopping at the first 403 or paywall. Metadata-only (title/citation-count from Semantic Scholar or OpenAlex, no full text read) is an acceptable fallback, not a default — if more than half the final table ends up unverified beyond a snippet, say so explicitly as a shortfall of the search, not just a footnote per row.
- Return an evidence table capped at **3–5 best sources**: title/author(s)/year/type, URL, a short supporting quote, and a quality line (citation count, venue, year — whatever is available).
- **Thesis-mode branches only:** tag each source support / challenge / complicate relative to that branch's position.
- Report which URLs it actually fetched and verified in-session, versus ones only seen in a search-result snippet.
- Not attempt any synthesis — structured findings only. Synthesis happens once, in step 4, by this skill.
- Say explicitly when a claim can't be backed by a real source, rather than asserting it anyway.

Leave the subagent's `model` unspecified unless the user requests a specific one for this invocation — deliberately left open for experimentation.

### 4. Single synthesis pass

Run this yourself — never delegate it to another subagent, and never repeat it. Exactly one pass, over the evidence table(s) already returned:

- **Thesis mode:** reconcile the two evidence tables into a synthesis noting where the thesis holds, where the antithesis holds, and where the evidence is contested or unclear. You may only cite sources already present in the two tables — never introduce a new claim at this step.
- **Topic mode:** compile the single evidence table into a scoping-style map of what's known, in the spirit of PRISMA-ScR (map the extent/range/nature of the evidence — no verdict, since there is no claim to adjudicate).
- In both modes, explicitly note where evidence was thin or unavailable (paywalled sources, no results) rather than filling the gap with an unsupported claim.
- Never run a second round of debate or research based on the synthesis — this skill is single-pass by design (see ADR-0002: iterated deliberation is documented to erode facts and homogenise stances).

### 5. Present and record

Present the full result — evidence table(s) plus synthesis/map — to the user and wait for approval or requested adjustments.

If this skill was invoked as part of an existing ticket's research (a `{{ISSUE_PREFIX}}-XX` ID was given, or is inferable from the conversation), write the findings into that ticket's `docs/knowledge/notes/{{ISSUE_PREFIX}}-XX.md`, following the existing per-ticket note format (dated heading under `## Notes`) — this is what `docs/workflows/RESEARCH.md` step 4 means by "capture findings mid-session, don't batch to the end." If invoked standalone, the conversation output is the deliverable; do not create a notes file for a ticket that doesn't exist.

---

## Notes

- This skill never implements anything — it produces a finding. If the finding leads to a decision to build something, that follows the normal `brief`/`plan` → `implement` path as a separate ticket.
- `docs/workflows/RESEARCH.md` step 2 ("survey existing alternatives") can invoke this skill directly for claims or topics that suit a literature search — it is not mandatory for every research ticket (e.g. surveying internal code precedent doesn't need it).
- Runs inline in the session rather than being dispatched wholesale to a single subagent, because it owns two approval gates (steps 2 and 5) and spawns its own nested subagents (step 3) — the same reason `debrief` stays inline.

---

## Constraints

- Never run more than one synthesis pass, in either mode.
- Never spawn more than two branch subagents in thesis mode, or more than one in topic mode.
- Never let the synthesis step introduce a claim absent from the evidence tables.
- Never fabricate a citation — every claim in the final output must carry a URL a subagent actually fetched or found via search.
- Never modify application code.
