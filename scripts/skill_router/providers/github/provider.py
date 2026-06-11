from __future__ import annotations

import subprocess

from .cli import _find_gh, _get_github_repo


_TOOLS_GITHUB = [
    {"type": "function", "function": {"name": "github_get_pr", "description": "Get PR details: title, state, head commit SHA, and changed files", "parameters": {"type": "object", "properties": {"number": {"type": "integer", "description": "PR number"}}, "required": ["number"]}}},
    {"type": "function", "function": {"name": "github_get_pr_diff", "description": "Get the full unified diff of a PR (truncated at 100 KB)", "parameters": {"type": "object", "properties": {"number": {"type": "integer"}}, "required": ["number"]}}},
    {"type": "function", "function": {"name": "github_create_pr_comment", "description": "Post a general comment on a PR", "parameters": {"type": "object", "properties": {"number": {"type": "integer"}, "body": {"type": "string"}}, "required": ["number", "body"]}}},
    {"type": "function", "function": {"name": "github_create_pr_review_comment", "description": "Post an inline review comment on a specific file and line in a PR", "parameters": {"type": "object", "properties": {"number": {"type": "integer"}, "commit_id": {"type": "string", "description": "Head commit SHA of the PR"}, "path": {"type": "string", "description": "File path relative to repo root"}, "line": {"type": "integer", "description": "Line number in the diff"}, "body": {"type": "string"}}, "required": ["number", "commit_id", "path", "line", "body"]}}},
    {"type": "function", "function": {"name": "github_merge_pr", "description": "Merge a pull request", "parameters": {"type": "object", "properties": {"number": {"type": "integer"}, "method": {"type": "string", "enum": ["merge", "squash", "rebase"], "description": "Merge method (default: squash)"}}, "required": ["number"]}}},
]


_GITHUB_TOOL_NAMES = {s["function"]["name"] for s in _TOOLS_GITHUB}


class GithubProvider:
    group_name = "github"

    def validate(self) -> str | None:
        return None

    def tools(self):
        return _TOOLS_GITHUB

    def handles(self, name: str) -> bool:
        return name in _GITHUB_TOOL_NAMES

    def dispatch(self, name: str, args: dict) -> str:
        gh = _find_gh()
        try:
            if name == "github_get_pr":
                r = subprocess.run(
                    [gh, "pr", "view", str(args["number"]), "--json", "title,state,headRefOid,files,body"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return r.stdout or r.stderr
            if name == "github_get_pr_diff":
                r = subprocess.run(
                    [gh, "pr", "diff", str(args["number"])],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                diff = r.stdout or r.stderr
                return (diff[:100_000] + "\n...[truncated]") if len(diff) > 100_000 else diff
            if name == "github_create_pr_comment":
                r = subprocess.run(
                    [gh, "pr", "comment", str(args["number"]), "--body", args["body"]],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return r.stdout + r.stderr
            if name == "github_create_pr_review_comment":
                repo = _get_github_repo()
                if not repo:
                    return "[github tool error] could not resolve owner/repo from git remote"
                r = subprocess.run(
                    [
                        gh, "api",
                        f"repos/{repo}/pulls/{args['number']}/comments",
                        "--method", "POST",
                        "--field", f"body={args['body']}",
                        "--field", f"commit_id={args['commit_id']}",
                        "--field", f"path={args['path']}",
                        "--field", f"line={args['line']}",
                        "--field", "side=RIGHT",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return r.stdout + r.stderr
            if name == "github_merge_pr":
                method = args.get("method", "squash")
                r = subprocess.run(
                    [gh, "pr", "merge", str(args["number"]), f"--{method}"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                return r.stdout + r.stderr
        except Exception as e:
            return f"[github tool error] {e}"
        return f"Unknown GitHub tool: {name}"
