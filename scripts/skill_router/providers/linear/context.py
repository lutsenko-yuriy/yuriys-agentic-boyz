from .client import _linear_graphql


ISSUES_QUERY = """
{
  issues(
    filter: { state: { type: { nin: ["completed", "cancelled"] } } }
    orderBy: updatedAt
    first: 50
  ) {
    nodes {
      identifier
      title
      description
      state { name type }
      labels { nodes { name } }
    }
  }
}
"""


def _build_milestones_query(project_id: str) -> str:
    return f"""
{{
  project(id: "{project_id}") {{
    projectMilestones {{
      nodes {{
        name
        progress
        targetDate
        status
      }}
    }}
  }}
}}
"""


def fetch_linear_context(api_key: str, project_id: str) -> dict:
    issues_data = _linear_graphql(api_key, ISSUES_QUERY)
    milestones_data = _linear_graphql(api_key, _build_milestones_query(project_id))
    return {
        "issues": issues_data.get("data", {}).get("issues", {}).get("nodes", []),
        "milestones": (
            milestones_data.get("data", {})
            .get("project", {})
            .get("projectMilestones", {})
            .get("nodes", [])
            if milestones_data.get("data", {}).get("project")
            else []
        ),
    }


def format_linear_context(data: dict) -> str:
    issues = data.get("issues", [])
    milestones = data.get("milestones", [])

    lines = [
        "=== PRE-FETCHED BACKLOG (output this verbatim, then ask the release question) ===",
        "",
        "## Backlog — Habit Loop",
        "",
    ]

    active = next(
        (m for m in milestones if m.get("status") not in ("done", "overdue", "canceled")),
        None,
    )
    lines.append(
        f"### Active milestone: {active['name']} ({active['progress']}% complete)"
        if active
        else "### Active milestone: none"
    )
    lines.append("")

    def _fmt_issue(i: dict) -> str:
        desc = (i.get("description") or "").split("\n")[0].strip()[:120]
        return f"- {i['identifier']}: {i['title']}" + (f" — {desc}" if desc else "")

    bugs = [i for i in issues if any(l["name"] in ("Bug", "Tech Debt") for l in i["labels"]["nodes"])]
    work = [i for i in issues if any(l["name"] in ("Feature", "Improvement") for l in i["labels"]["nodes"])]
    unlabeled = [i for i in issues if not i["labels"]["nodes"]]

    lines.append("### Issues (bugs & tech debt)")
    lines.extend(_fmt_issue(i) for i in bugs) if bugs else lines.append("_(none)_")
    lines.append("")

    lines.append("### Remaining work")
    all_work = work + unlabeled
    lines.extend(_fmt_issue(i) for i in all_work) if all_work else lines.append("_(none)_")
    lines.append("")

    lines.append("=== END PRE-FETCHED BACKLOG ===")
    return "\n".join(lines)
