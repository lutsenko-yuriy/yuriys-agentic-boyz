from __future__ import annotations

from .protocols import ToolProvider, ToolSchema, ToolName, ToolArgs, ToolResult


class ProviderRegistry:
    def __init__(self, providers: list[ToolProvider]):
        self._providers = providers
        self._by_name: dict[str, ToolProvider] = {}
        for p in providers:
            for schema in p.tools():
                self._by_name[schema["function"]["name"]] = p

    def tool_schemas(self) -> list[ToolSchema]:
        return [s for p in self._providers for s in p.tools()]

    def dispatch(self, name: ToolName, args: ToolArgs) -> ToolResult:
        provider = self._by_name.get(name)
        if provider is None:
            return f"[tool error] unknown tool: {name}"
        try:
            return provider.dispatch(name, args)
        except Exception as e:
            return f"[{provider.group_name} tool error] {e}"
