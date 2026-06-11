from __future__ import annotations

import subprocess
from pathlib import Path


_TOOLS_FILES = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a file from the project root", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Path relative to project root"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write (create or overwrite) a file in the project root", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "run_bash", "description": "Run a shell command in the project root and return stdout + stderr", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
]


_FILES_TOOL_NAMES = {s["function"]["name"] for s in _TOOLS_FILES}


class FilesProvider:
    group_name = "files"

    def __init__(self, project_root: str = "."):
        self._project_root = project_root

    def project_root(self) -> str:
        return self._project_root

    def validate(self) -> str | None:
        return None

    def tools(self):
        return _TOOLS_FILES

    def handles(self, name: str) -> bool:
        return name in _FILES_TOOL_NAMES

    def dispatch(self, name: str, args: dict) -> str:
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
                    args["command"], shell=True, capture_output=True, text=True, timeout=120
                )
                out = r.stdout
                if r.stderr:
                    out += f"\n[stderr]\n{r.stderr}"
                return out or "(no output)"
        except Exception as e:
            return f"[files tool error] {e}"
        return f"Unknown files tool: {name}"
