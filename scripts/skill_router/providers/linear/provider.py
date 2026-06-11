from __future__ import annotations

import json

from .client import _linear_graphql
from .context import fetch_linear_context, format_linear_context, ISSUES_QUERY


_GET_ISSUE_QUERY = """
query($id: String!) {
  issue(id: $id) {
    id
    identifier
    title
    description
    state { id name type }
    labels { nodes { id name } }
    team { id name }
    comments { nodes { id body createdAt } }
  }
}
"""

_LIST_STATES_QUERY = """
query($teamId: String!) {
  team(id: $teamId) {
    states { nodes { id name type } }
  }
}
"""

_UPDATE_ISSUE_MUTATION = """
mutation($id: String!, $stateId: String!) {
  issueUpdate(id: $id, input: {stateId: $stateId}) {
    success
    issue { identifier state { name } }
  }
}
"""

_CREATE_COMMENT_MUTATION = """
mutation($issueId: String!, $body: String!) {
  commentCreate(input: {issueId: $issueId, body: $body}) {
    success
    comment { id }
  }
}
"""


_TOOLS_LINEAR = [
    {"type": "function", "function": {"name": "linear_list_issues", "description": "List open issues from the Linear workspace", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "linear_get_issue", "description": "Get full details of a Linear issue by identifier (e.g. HAB-42)", "parameters": {"type": "object", "properties": {"identifier": {"type": "string", "description": "Issue identifier e.g. HAB-42"}}, "required": ["identifier"]}}},
    {"type": "function", "function": {"name": "linear_update_issue_state", "description": "Move a Linear issue to a new workflow state", "parameters": {"type": "object", "properties": {"identifier": {"type": "string", "description": "Issue identifier e.g. HAB-42"}, "state_name": {"type": "string", "description": "Target state name e.g. 'In Review', 'In QA', 'Done', 'In Progress'"}}, "required": ["identifier", "state_name"]}}},
    {"type": "function", "function": {"name": "linear_create_comment", "description": "Post a comment on a Linear issue", "parameters": {"type": "object", "properties": {"identifier": {"type": "string", "description": "Issue identifier e.g. HAB-42"}, "body": {"type": "string", "description": "Comment text (Markdown)"}}, "required": ["identifier", "body"]}}},
]


_LINEAR_TOOL_NAMES = {s["function"]["name"] for s in _TOOLS_LINEAR}


class LinearProvider:
    group_name = "linear"

    def __init__(self, api_key: str | None, project_id: str | None):
        self._api_key = api_key
        self._project_id = project_id

    def validate(self) -> str | None:
        if not self._api_key:
            return "LINEAR_API_KEY not set — required for the 'linear' tool group"
        return None

    def tools(self):
        return _TOOLS_LINEAR

    def handles(self, name: str) -> bool:
        return name in _LINEAR_TOOL_NAMES

    def dispatch(self, name: str, args: dict) -> str:
        api_key = self._api_key
        try:
            if name == "linear_list_issues":
                data = _linear_graphql(api_key, ISSUES_QUERY)
                return json.dumps(data.get("data", {}).get("issues", {}).get("nodes", []))

            if name == "linear_get_issue":
                data = _linear_graphql(api_key, _GET_ISSUE_QUERY, {"id": args["identifier"]})
                issue = data.get("data", {}).get("issue")
                return json.dumps(issue) if issue else f"Issue {args['identifier']} not found"

            if name == "linear_update_issue_state":
                identifier, state_name = args["identifier"], args["state_name"]
                issue_data = _linear_graphql(api_key, _GET_ISSUE_QUERY, {"id": identifier})
                issue = issue_data.get("data", {}).get("issue")
                if not issue:
                    return f"Issue {identifier} not found"
                team_id = issue["team"]["id"]
                states_data = _linear_graphql(api_key, _LIST_STATES_QUERY, {"teamId": team_id})
                states = states_data.get("data", {}).get("team", {}).get("states", {}).get("nodes", [])
                state = next((s for s in states if s["name"].lower() == state_name.lower()), None)
                if not state:
                    return f"State '{state_name}' not found. Available: {[s['name'] for s in states]}"
                result = _linear_graphql(api_key, _UPDATE_ISSUE_MUTATION, {"id": issue["id"], "stateId": state["id"]})
                return json.dumps(result.get("data", {}).get("issueUpdate", {}))

            if name == "linear_create_comment":
                issue_data = _linear_graphql(api_key, _GET_ISSUE_QUERY, {"id": args["identifier"]})
                issue = issue_data.get("data", {}).get("issue")
                if not issue:
                    return f"Issue {args['identifier']} not found"
                result = _linear_graphql(api_key, _CREATE_COMMENT_MUTATION, {"issueId": issue["id"], "body": args["body"]})
                return json.dumps(result.get("data", {}).get("commentCreate", {}))

        except Exception as e:
            return f"[linear tool error] {e}"

        return f"Unknown Linear tool: {name}"

    def fetch_context(self) -> dict:
        return fetch_linear_context(self._api_key, self._project_id)

    def format_context(self, data: dict) -> str:
        return format_linear_context(data)
