# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
skill_router.py — routes a skill to the LM Studio local OpenAI-compatible API.

Usage:
    python scripts/skill_router.py <skill_path> [--args <extra>]

Arguments:
    skill_path   Path to the SKILL.md file (e.g. skills/manage/ship/SKILL.md)
    --args       Optional extra text appended to the skill prompt (e.g. "PR #115")

Exit codes:
    0  Skill executed successfully
    1  LM Studio unavailable or the mapped model is not loaded
    2  Skill file not found, unparseable frontmatter, or no lm-studio mapping
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

LMSTUDIO_BASE = "http://localhost:1234/v1"
MODEL_TIERS_PATH = "docs/MODEL_TIERS.md"
LINEAR_API_URL = "https://api.linear.app/graphql"
LINEAR_PROJECT_ID = "c3afdc26-d306-4f72-bdb3-de9b01060d0f"
MAX_TOOL_TURNS = 40

# ---------------------------------------------------------------------------
# Linear GraphQL queries / mutations
# ---------------------------------------------------------------------------

_ISSUES_QUERY = f"""
{{
  issues(
    filter: {{ state: {{ type: {{ nin: ["completed", "cancelled"] }} }} }}
    orderBy: updatedAt
    first: 50
  ) {{
    nodes {{
      identifier
      title
      description
      state {{ name type }}
      labels {{ nodes {{ name }} }}
    }}
  }}
}}
"""

_MILESTONES_QUERY = f"""
{{
  project(id: "{LINEAR_PROJECT_ID}") {{
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

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling format)
# ---------------------------------------------------------------------------

_TOOLS_LINEAR = [
    {
        "type": "function",
        "function": {
            "name": "linear_list_issues",
            "description": "List open issues from the Linear workspace",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "linear_get_issue",
            "description": "Get full details of a Linear issue by identifier (e.g. HAB-42)",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Issue identifier e.g. HAB-42"},
                },
                "required": ["identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "linear_update_issue_state",
            "description": "Move a Linear issue to a new workflow state",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Issue identifier e.g. HAB-42"},
                    "state_name": {
                        "type": "string",
                        "description": "Target state name e.g. 'In Review', 'In QA', 'Done', 'In Progress'",
                    },
                },
                "required": ["identifier", "state_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "linear_create_comment",
            "description": "Post a comment on a Linear issue",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Issue identifier e.g. HAB-42"},
                    "body": {"type": "string", "description": "Comment text (Markdown)"},
                },
                "required": ["identifier", "body"],
            },
        },
    },
]

_TOOLS_GITHUB = [
    {
        "type": "function",
        "function": {
            "name": "github_get_pr",
            "description": "Get PR details: title, state, head commit SHA, and changed files",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer", "description": "PR number"},
                },
                "required": ["number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_get_pr_diff",
            "description": "Get the full unified diff of a PR (truncated at 100 KB)",
            "parameters": {
                "type": "object",
                "properties": {"number": {"type": "integer"}},
                "required": ["number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_create_pr_comment",
            "description": "Post a general comment on a PR",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "body": {"type": "string"},
                },
                "required": ["number", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_create_pr_review_comment",
            "description": "Post an inline review comment on a specific file and line in a PR",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "commit_id": {"type": "string", "description": "Head commit SHA of the PR"},
                    "path": {"type": "string", "description": "File path relative to repo root"},
                    "line": {"type": "integer", "description": "Line number in the diff"},
                    "body": {"type": "string"},
                },
                "required": ["number", "commit_id", "path", "line", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_merge_pr",
            "description": "Merge a pull request",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "method": {
                        "type": "string",
                        "enum": ["merge", "squash", "rebase"],
                        "description": "Merge method (default: squash)",
                    },
                },
                "required": ["number"],
            },
        },
    },
]

_TOOLS_FILES = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project root",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to project root"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write (create or overwrite) a file in the project root",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Run a shell command in the project root and return stdout + stderr",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
]


_KNOWN_TOOL_GROUPS = {"linear", "github", "files"}


def _build_tools(groups: list) -> list:
    """Assemble OpenAI tool-definition list for the given group names."""
    tools = []
    for g in groups:
        if g == "linear":
            tools.extend(_TOOLS_LINEAR)
        elif g == "github":
            tools.extend(_TOOLS_GITHUB)
        elif g == "files":
            tools.extend(_TOOLS_FILES)
        else:
            print(f"[skill_router] Unknown tool group '{g}' — skipping", file=sys.stderr)
    return tools


# ---------------------------------------------------------------------------
# Linear GraphQL helper (extended to support variables)
# ---------------------------------------------------------------------------

def _linear_graphql(api_key: str, query: str, variables: dict = None) -> dict:
    """Execute a GraphQL query/mutation against the Linear API. Raises on HTTP errors."""
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        LINEAR_API_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


def fetch_linear_context(api_key: str) -> dict:
    """Fetch open issues and project milestones from Linear. Returns {issues, milestones}."""
    issues_data = _linear_graphql(api_key, _ISSUES_QUERY)
    milestones_data = _linear_graphql(api_key, _MILESTONES_QUERY)
    return {
        "issues": issues_data.get("data", {}).get("issues", {}).get("nodes", []),
        "milestones": (
            milestones_data.get("data", {})
            .get("project", {})
            .get("projectMilestones", {})
            .get("nodes", [])
        ),
    }


def format_linear_context(data: dict) -> str:
    """Format fetched Linear data as ready-to-output markdown for the skill prompt.

    Produces the final backlog markdown directly so the model copies it verbatim
    rather than re-interpreting a data block through a template.
    """
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


# ---------------------------------------------------------------------------
# Auth / tool execution helpers
# ---------------------------------------------------------------------------

def _auth_headers() -> dict:
    """Return Authorization header dict if LM_API_TOKEN env var is set, else empty dict."""
    token = os.environ.get("LM_API_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _find_gh() -> str:
    """Return path to the gh CLI binary."""
    import shutil
    return shutil.which("gh") or "/opt/homebrew/bin/gh"


def _get_github_repo() -> str:
    """Return 'owner/repo' resolved from git remote origin."""
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", r.stdout.strip())
        return m.group(1) if m else ""
    except Exception:
        return ""


def _execute_linear_tool(name: str, args: dict, api_key: str) -> str:
    """Execute a linear_* tool call and return a JSON string result."""
    try:
        if name == "linear_list_issues":
            data = _linear_graphql(api_key, _ISSUES_QUERY)
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


def _execute_github_tool(name: str, args: dict) -> str:
    """Execute a github_* tool call using the gh CLI."""
    gh = _find_gh()
    try:
        if name == "github_get_pr":
            r = subprocess.run(
                [gh, "pr", "view", str(args["number"]),
                 "--json", "title,state,headRefOid,files,body"],
                capture_output=True, text=True, timeout=30,
            )
            return r.stdout or r.stderr

        if name == "github_get_pr_diff":
            r = subprocess.run(
                [gh, "pr", "diff", str(args["number"])],
                capture_output=True, text=True, timeout=30,
            )
            diff = r.stdout or r.stderr
            return (diff[:100_000] + "\n...[truncated]") if len(diff) > 100_000 else diff

        if name == "github_create_pr_comment":
            r = subprocess.run(
                [gh, "pr", "comment", str(args["number"]), "--body", args["body"]],
                capture_output=True, text=True, timeout=30,
            )
            return r.stdout + r.stderr

        if name == "github_create_pr_review_comment":
            repo = _get_github_repo()
            if not repo:
                return "[github tool error] could not resolve owner/repo from git remote"
            r = subprocess.run(
                [
                    gh, "api", f"repos/{repo}/pulls/{args['number']}/comments",
                    "--method", "POST",
                    "--field", f"body={args['body']}",
                    "--field", f"commit_id={args['commit_id']}",
                    "--field", f"path={args['path']}",
                    "--field", f"line={args['line']}",
                    "--field", "side=RIGHT",
                ],
                capture_output=True, text=True, timeout=30,
            )
            return r.stdout + r.stderr

        if name == "github_merge_pr":
            method = args.get("method", "squash")
            r = subprocess.run(
                [gh, "pr", "merge", str(args["number"]), f"--{method}"],
                capture_output=True, text=True, timeout=60,
            )
            return r.stdout + r.stderr

    except Exception as e:
        return f"[github tool error] {e}"

    return f"Unknown GitHub tool: {name}"


def _execute_files_tool(name: str, args: dict) -> str:
    """Execute read_file / write_file / run_bash tool calls."""
    try:
        if name == "read_file":
            return Path(args["path"]).read_text()

        if name == "write_file":
            p = Path(args["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"])
            return f"Written {args['path']}"

        if name == "run_bash":
            r = subprocess.run(
                args["command"], shell=True,
                capture_output=True, text=True, timeout=120,
            )
            out = r.stdout
            if r.stderr:
                out += f"\n[stderr]\n{r.stderr}"
            return out or "(no output)"

    except Exception as e:
        return f"[files tool error] {e}"

    return f"Unknown files tool: {name}"


def _execute_tool(name: str, args: dict, *, linear_api_key: str = None) -> str:
    """Dispatch a tool call to the correct executor."""
    if name.startswith("linear_"):
        if not linear_api_key:
            return "[tool error] LINEAR_API_KEY not set — required for linear_* tools"
        return _execute_linear_tool(name, args, linear_api_key)
    if name.startswith("github_"):
        return _execute_github_tool(name, args)
    if name in ("read_file", "write_file", "run_bash"):
        return _execute_files_tool(name, args)
    return f"[tool error] unknown tool: {name}"


# ---------------------------------------------------------------------------
# Multi-turn tool-calling completion loop
# ---------------------------------------------------------------------------

def chat_completion_with_tools(
    model_name: str,
    prompt: str,
    tools: list,
    *,
    linear_api_key: str = None,
    max_turns: int = MAX_TOOL_TURNS,
) -> bool:
    """Run a multi-turn tool-calling loop, printing the final response to stdout.

    Uses non-streaming for all turns so tool-call JSON is trivial to parse.
    Returns True on success, False on error.
    """
    messages = [{"role": "user", "content": prompt}]

    for turn in range(max_turns):
        payload = json.dumps({
            "model": model_name,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            f"{LMSTUDIO_BASE}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", **_auth_headers()},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.load(resp)
        except Exception as e:
            print(f"\n[skill_router] Tool loop error on turn {turn + 1}: {e}", file=sys.stderr)
            return False

        if not data.get("choices"):
            print("[skill_router] Empty response from model", file=sys.stderr)
            return False

        choice = data["choices"][0]
        msg = choice["message"]
        finish_reason = choice.get("finish_reason", "stop")
        tool_calls = msg.get("tool_calls") or []

        if tool_calls and finish_reason in ("tool_calls", None, ""):
            messages.append(msg)
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except (json.JSONDecodeError, TypeError):
                    fn_args = {}
                print(
                    f"[tool:{turn + 1}] {fn_name}({json.dumps(fn_args)[:120]})",
                    file=sys.stderr,
                )
                result = _execute_tool(fn_name, fn_args, linear_api_key=linear_api_key)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result if isinstance(result, str) else json.dumps(result),
                })
        else:
            content = msg.get("content") or ""
            print(content, flush=True)
            print()
            return True

    print(f"[skill_router] Tool loop hit max turns ({max_turns})", file=sys.stderr)
    return False


# ---------------------------------------------------------------------------
# Frontmatter / model resolution
# ---------------------------------------------------------------------------

def read_frontmatter(skill_path: str):
    """Return (effort, reasoning, needs_session_tools, context, tools, max_turns, body).

    tools is a list of group names parsed from the comma-separated `tools:` field,
    e.g. 'linear,github,files' → ['linear', 'github', 'files'].
    max_turns defaults to MAX_TOOL_TURNS when the frontmatter field is absent.
    """
    text = Path(skill_path).read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None, None, False, None, [], MAX_TOOL_TURNS, text
    fm = m.group(1)
    effort = re.search(r"^effort:\s*(\S+)", fm, re.MULTILINE)
    reasoning = re.search(r"^reasoning:\s*(\S+)", fm, re.MULTILINE)
    needs_session_tools = bool(re.search(r"^needs_session_tools:\s*true", fm, re.MULTILINE))
    context_match = re.search(r"^context:\s*(\S+)", fm, re.MULTILINE)
    tools_match = re.search(r"^tools:\s*(.+)$", fm, re.MULTILINE)
    tools = [t.strip() for t in tools_match.group(1).split(",")] if tools_match else []
    max_turns_match = re.search(r"^max_turns:\s*(\d+)", fm, re.MULTILINE)
    max_turns = int(max_turns_match.group(1)) if max_turns_match else MAX_TOOL_TURNS
    return (
        effort.group(1) if effort else None,
        reasoning.group(1) if reasoning else None,
        needs_session_tools,
        context_match.group(1) if context_match else None,
        tools,
        max_turns,
        text[m.end():],
    )


def _normalize_model_name(name: str) -> str:
    """Strip quantization annotations (e.g. '(MLX, 4-bit)') and lowercase."""
    return re.split(r"[\s(]", name.strip())[0].lower()


def lookup_lmstudio_model(effort: str, reasoning: str):
    """
    Scan the Active mapping table in MODEL_TIERS.md.
    Returns the model name if the alias is 'lm-studio', else None.

    Expected table row format (after splitting on '|' and stripping):
        index 0: ''   index 1: Effort   index 2: Reasoning
        index 3: Model   index 4: alias   index 5: ''
    Rows with fewer than 5 parts (header separators, blank lines) are skipped.
    """
    try:
        tiers_text = Path(MODEL_TIERS_PATH).read_text()
    except FileNotFoundError:
        print(f"[skill_router] {MODEL_TIERS_PATH} not found", file=sys.stderr)
        return None

    section = re.search(r"## Active mapping\n(.*?)\n---", tiers_text, re.DOTALL)
    if not section:
        print(f"[skill_router] '## Active mapping' section not found in {MODEL_TIERS_PATH}", file=sys.stderr)
        return None

    for line in section.group(1).splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5:
            continue
        row_effort, row_reasoning, model, alias = parts[1], parts[2], parts[3], parts[4]
        if row_effort == effort and row_reasoning == reasoning:
            clean_alias = alias.strip("`")
            return model if clean_alias == "lm-studio" else None

    return None


def model_loaded(model_name: str) -> bool:
    """Return True if LM Studio is reachable and the model is loaded.

    Compares normalized base names (strips quantization annotations like
    '(MLX, 4-bit)') so 'qwen/qwen3-8b (MLX, 4-bit)' matches a LM Studio
    id like 'qwen/qwen3-8b' or 'qwen/qwen3-8b-mlx'.
    """
    try:
        req = urllib.request.Request(f"{LMSTUDIO_BASE}/models", headers=_auth_headers())
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.load(resp)
        loaded_ids = [m["id"] for m in data.get("data", [])]
        needle = _normalize_model_name(model_name)
        return any(
            needle in _normalize_model_name(mid) or _normalize_model_name(mid) in needle
            for mid in loaded_ids
        )
    except Exception:
        return False


def stream_completion(model_name: str, prompt: str) -> bool:
    """POST a streaming chat completion and write chunks to stdout."""
    payload = json.dumps(
        {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
    ).encode()
    req = urllib.request.Request(
        f"{LMSTUDIO_BASE}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", **_auth_headers()},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw_line in resp:
                line = raw_line.decode().strip()
                if not line.startswith("data: "):
                    continue
                payload_str = line[6:]
                if payload_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload_str)
                    content = chunk["choices"][0]["delta"].get("content", "")
                    if content:
                        print(content, end="", flush=True)
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    pass
        print()  # trailing newline
        return True
    except Exception as e:
        print(f"\n[skill_router] Streaming error: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: skill_router.py <skill_path> [--args <extra>]", file=sys.stderr)
        sys.exit(2)

    skill_path = sys.argv[1]

    # Parse --args flag (everything after --args is the extra context)
    extra_args = ""
    if "--args" in sys.argv:
        idx = sys.argv.index("--args")
        extra_args = " ".join(sys.argv[idx + 1:]).strip()

    if not Path(skill_path).exists():
        print(f"[skill_router] Skill file not found: {skill_path}", file=sys.stderr)
        sys.exit(2)

    effort, reasoning, needs_session_tools, context, tool_groups, max_turns, body = read_frontmatter(skill_path)
    if not effort or not reasoning:
        print(f"[skill_router] Could not parse frontmatter in {skill_path}", file=sys.stderr)
        sys.exit(2)

    if needs_session_tools:
        print(
            f"[skill_router] {skill_path} requires session tools (MCP/Bash/Edit) — "
            "must run inside Claude Code, not via LM Studio",
            file=sys.stderr,
        )
        sys.exit(2)

    # Pre-inject Linear context if requested
    if context == "linear":
        api_key = os.environ.get("LINEAR_API_KEY")
        if not api_key:
            print(
                "[skill_router] LINEAR_API_KEY not set — required for skills with context: linear",
                file=sys.stderr,
            )
            sys.exit(2)
        try:
            context_data = fetch_linear_context(api_key)
            body = f"{format_linear_context(context_data)}\n\n{body}"
        except Exception as e:
            print(f"[skill_router] Failed to fetch Linear context: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate LINEAR_API_KEY is present when linear tools are requested
    linear_api_key = os.environ.get("LINEAR_API_KEY")
    if "linear" in tool_groups and not linear_api_key:
        print(
            "[skill_router] LINEAR_API_KEY not set — required for skills with tools: linear",
            file=sys.stderr,
        )
        sys.exit(2)

    model_name = lookup_lmstudio_model(effort, reasoning)
    if not model_name:
        print(
            f"[skill_router] No lm-studio mapping for {effort}+{reasoning} in {MODEL_TIERS_PATH}",
            file=sys.stderr,
        )
        sys.exit(2)

    if not model_loaded(model_name):
        print(
            f"[skill_router] LM Studio unavailable or model not loaded: {model_name}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Strip quantization annotations (e.g. "(MLX, 4-bit)") — LM Studio rejects them
    api_model_name = _normalize_model_name(model_name)
    prompt = f"{body}\n\n---\n\n{extra_args}" if extra_args else body

    tools = _build_tools(tool_groups)
    if tools:
        success = chat_completion_with_tools(
            api_model_name, prompt, tools, linear_api_key=linear_api_key, max_turns=max_turns
        )
    else:
        success = stream_completion(api_model_name, prompt)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
