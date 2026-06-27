---
name: brief
effort: FOCUSED
reasoning: ARCHITECTURAL
output_style: CONCISE
description: Guide the user through articulating a rough feature idea and turn it into a properly scoped ticket. Reads the product spec and glossary, engages in an iterative clarifying dialog (one question at a time), then creates the ticket and updates the glossary. When called with an existing ticket ID, first checks whether that ticket's description still reflects reality and offers to update it. Invoked from the summarize flow when the user wants to describe something new rather than pick up an existing ticket.
---

@skills/shared/project-config.md

This skill produces a ticket, not code.

---

## Steps

### 0. Existing ticket check (only when called with a ticket ID)

If the user invokes this skill with an existing issue ID (e.g. `/brief {{ISSUE_PREFIX}}-XX`):

1. Fetch the issue (PM mapping: **Fetch issue**).
2. Read `docs/PRODUCT_SPEC.md` and `docs/GLOSSARY.md`.
3. Compare the ticket description against the current product context and both repos' actual state (read relevant files if needed).
4. Present a one-paragraph assessment: is the description still accurate, partially stale, or significantly out of date?
5. Ask: *"Does this description still reflect what you want to build, or should we revise it?"*
   - If the user confirms it is still accurate: proceed directly to step 4 (create/update is a no-op; skip dialog).
   - If the user wants revisions: open the dialog (step 2) with the existing description as context, then update the ticket at step 4 instead of creating a new one.

---

### 1. Read product context

Read the following files in full before asking the user anything:

- **Product spec** (`docs/PRODUCT_SPEC.md`) — what the product currently does
- **Glossary** (`docs/GLOSSARY.md`) — canonical domain terms and known aliases

This context is the reference against which the user's idea will be validated.

### 2. Open the dialog

Ask the user to describe their feature idea in their own words. One open question is enough:

> "Tell me about the feature you have in mind."

### 3. Iterate — one question at a time

**Spirit of the dialog:** the goal is mutual clarity — the user ends the conversation with a shared, unambiguous picture of what they want to build.

@skills/shared/dialog-principles.md

**Staying on topic:** the dialog has a clear goal — a scoped ticket. If the conversation drifts (the user starts discussing unrelated ideas, broader strategy, or goes off on a tangent), gently acknowledge what was said and redirect: "That's interesting — let's note it and come back. For now, can we finish pinning down [the feature we started with]?" Do not chase tangents, even interesting ones.

**Abstraction / porting trigger:** if the idea involves abstracting, extracting, or porting (key words: "generalise", "extract", "port", "make portable"), ask as one of the clarifying questions:

> "Where is the boundary? What must move to the shared layer, and what can stay project-specific?"

Do not proceed to step 4 until the boundary is explicitly agreed.

After each user response, do exactly one of the following:

- **Ask one clarifying question** — if anything is ambiguous, undefined, or contradicts the spec or glossary. Do not ask multiple questions at once.
- **Flag a contradiction** — if the idea conflicts with existing product behaviour, name the conflict and ask how the user wants to resolve it.
- **Flag an undefined term** — if the user introduces a term not in `docs/GLOSSARY.md`, ask them to define it before continuing.
- **Proceed to step 4** — if the idea is clear, coherent, and non-contradictory.

The dialog is **product-level only**: no architecture, no implementation details, no data models. The goal is clarity on *what* and *why*, not *how*.

If at any point the user signals abandonment ("I guess we don't need it", "let's postpone", "forget it", or similar), jump to step 6.

### 3.5 Visual alignment (for features with user-facing screens)

Once the behaviour is clear, ask the user for a visual reference or metaphor:

> "What does this screen look like in your head — is there an app or real-world analogy that captures the feel you're after?"

Based on the answer, produce a simple ASCII mockup and present it for approval before proceeding to step 4. If the user has no strong reference, propose one based on platform conventions. Do not proceed to step 4 until the layout direction is agreed.

### 4. Create or update the ticket

Once the idea is clear, create a new issue or update the existing one (PM mapping: **Create issue** / **Update issue**) using the **Team ID** and **Project ID** from the PM tool mapping:

- `team`: team ID from project config
- `project`: project ID from project config
- `title`: concise noun-phrase title
- `labels`: `["Feature"]`
- `priority`: 3 (Medium) unless the user indicated otherwise
- `description`: use the template below

**Ticket description template:**

```markdown
## User story

As a <role>, I want <action> so that <outcome>.

## Behaviour

<bullet list of observable behaviours — what the user sees and can do>

## Out of scope

<explicit list of things this ticket does NOT cover>

## Open questions

<any remaining ambiguities, or "None" if fully resolved>
```

Fill every section. "Out of scope" must always be present — even if short — to prevent scope creep.

### 5. Update the glossary (if new terms were introduced)

If the dialog produced any new domain terms not already in `docs/GLOSSARY.md`, add them now.

Open the glossary file, locate the correct alphabetical position, and insert entries following the existing format. Do not remove or reorder existing entries.

### 6. Report back

Tell the user:

- The ticket ID and URL (new or updated)
- Any glossary additions (term + definition), or "no glossary changes" if none

If the user abandoned in step 3:

- Summarise what was unclear or contradictory (2–4 bullet points)
- State that no ticket was created
- Stop

---

## Constraints

- Never ask more than one question per turn.
- Never discuss implementation, architecture, or data models.
- Never create a ticket until the idea is unambiguous and coherent.
- Never update the product spec (`docs/PRODUCT_SPEC.md`) — that is deferred to the post-implementation doc update in `ship`.
- Never update the backlog or changelog — those are owned by the `ship` skill.
