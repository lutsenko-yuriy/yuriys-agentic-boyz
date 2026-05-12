---
name: analyze
effort: FOCUSED
reasoning: ARCHITECTURAL
output_style: DETAILED
description: Analytics planning for a feature before implementation begins. Identifies the user-facing actions and screens introduced by a task, proposes which events and screen views to track, flags PII concerns, and updates docs/ANALYTICS_EVENTS.md after approval. Invoke for any feature or change with user-visible screens or interactions, before `plan` or `implement`.
---

The project management tool is **{{PM_TOOL}}**. The issue identifier prefix is **{{ISSUE_PREFIX}}**.

This skill produces an analytics plan, not code.

---

## Steps

### 1. Fetch the issue

Retrieve the full details of the issue (title, description, acceptance criteria, mockups or flow descriptions).

| Tool | How |
|---|---|
| Linear | `mcp__linear__get_issue` |
| Jira | `GET /rest/api/3/issue/{key}` |
| GitHub Issues | `gh issue view {number}` |
| GitLab | `glab issue view {number}` |

### 2. Read the existing analytics catalogue

Read `docs/ANALYTICS_EVENTS.md` in full to understand what is already tracked and avoid proposing duplicates.

### 3. Read the product context

Read `docs/PRODUCT_SPEC.md` and any relevant source files to understand the user journey this feature sits within. Look for existing screen names, navigation patterns, and event naming conventions already used in the codebase.

### 4. Identify trackable moments

Walk through the feature from the user's perspective and identify:

- **Screen views** — every distinct screen or modal the user lands on
- **Actions** — every deliberate user action (taps, submissions, selections, dismissals)
- **Outcomes** — results that matter for product understanding (success, failure, abandonment)
- **Transitions** — navigating between states where understanding drop-off is valuable

For each moment, ask: *Would a product or growth team make a decision based on this data?* If no, omit it.

### 5. Flag PII risks

For each proposed event and property, assess:
- Does the value identify a specific user or reveal sensitive behaviour?
- Is it safe to send to a third-party analytics service?

Mark any property carrying PII risk with `⚠️ PII` and propose a safe alternative (e.g. hash, bucketed value, or omission).

### 6. Propose the analytics plan

Present the proposal in this format. Omit a section if empty.

```
## Analytics plan — {{ISSUE_PREFIX}}-XX: <title>

### Screen views
| Screen name | Trigger | Properties |
|---|---|---|
| <name> | <when it fires> | <key: type — description> |

### Events
| Event name | Trigger | Properties |
|---|---|---|
| <name> | <when it fires> | <key: type — description ⚠️ PII if applicable> |

### Not tracked (and why)
- <moment>: <reason — too granular, not actionable, already covered by existing event>

### Open questions
- <anything that requires a product decision before finalising>
```

Follow the naming conventions already present in `docs/ANALYTICS_EVENTS.md`. If no convention exists yet, use `snake_case` for event names and `screen_<name>` for screen views.

### 7. Wait for approval

Present the plan and ask:

> "Does this analytics plan look right? Confirm or adjust before I update the catalogue."

Do not proceed until the user explicitly approves or provides corrections.

### 8. Update the analytics catalogue

Open `docs/ANALYTICS_EVENTS.md` and append the approved entries to the appropriate sections (Events, Screen Views). Include the issue reference in a comment or note so the origin is traceable.

Do not modify existing entries — only append.

### 9. Report back

Confirm what was added to `docs/ANALYTICS_EVENTS.md`. Remind the orchestrator that `implement` should include the instrumentation calls defined here.
