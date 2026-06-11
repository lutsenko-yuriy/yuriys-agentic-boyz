from __future__ import annotations

from typing import Protocol, runtime_checkable

ToolSchema = dict
ToolName = str
ToolArgs = dict
ToolResult = str


@runtime_checkable
class ToolProvider(Protocol):
    group_name: str

    def tools(self) -> list[ToolSchema]: ...
    def handles(self, name: ToolName) -> bool: ...
    def dispatch(self, name: ToolName, args: ToolArgs) -> ToolResult: ...
    def validate(self) -> str | None: ...


class PMToolProvider(ToolProvider, Protocol):
    def fetch_context(self) -> dict: ...
    def format_context(self, data: dict) -> str: ...


class FilesToolProvider(ToolProvider, Protocol):
    def project_root(self) -> str: ...
