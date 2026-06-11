import unittest

from skill_router.agentic.registry import ProviderRegistry


class _FakeProvider:
    """Duck-typed provider for testing registry behaviour."""

    def __init__(self, group_name, tool_names, dispatch_result=None, raise_on_dispatch=None):
        self.group_name = group_name
        self._tool_names = tool_names
        self._dispatch_result = dispatch_result if dispatch_result is not None else "ok"
        self._raise_on_dispatch = raise_on_dispatch
        self.dispatch_calls = []

    def tools(self):
        return [
            {"type": "function", "function": {"name": n, "description": "", "parameters": {}}}
            for n in self._tool_names
        ]

    def handles(self, name):
        return name in self._tool_names

    def dispatch(self, name, args):
        self.dispatch_calls.append((name, args))
        if self._raise_on_dispatch:
            raise self._raise_on_dispatch
        return self._dispatch_result

    def validate(self):
        return None


class TestProviderRegistry(unittest.TestCase):

    def test_aggregates_tool_schemas_from_all_providers(self):
        p1 = _FakeProvider("linear", ["linear_list_issues", "linear_get_issue"])
        p2 = _FakeProvider("files", ["read_file"])
        registry = ProviderRegistry([p1, p2])
        names = [s["function"]["name"] for s in registry.tool_schemas()]
        self.assertEqual(names, ["linear_list_issues", "linear_get_issue", "read_file"])

    def test_dispatch_routes_to_correct_provider(self):
        p1 = _FakeProvider("linear", ["linear_get_issue"], dispatch_result="linear-result")
        p2 = _FakeProvider("files", ["read_file"], dispatch_result="file-content")
        registry = ProviderRegistry([p1, p2])
        self.assertEqual(registry.dispatch("read_file", {"path": "x"}), "file-content")
        self.assertEqual(p2.dispatch_calls, [("read_file", {"path": "x"})])
        self.assertEqual(p1.dispatch_calls, [])

    def test_dispatch_returns_error_string_for_unknown_tool(self):
        p1 = _FakeProvider("linear", ["linear_get_issue"])
        registry = ProviderRegistry([p1])
        result = registry.dispatch("nonexistent_tool", {})
        self.assertIn("unknown tool", result)
        self.assertIn("nonexistent_tool", result)

    def test_dispatch_catches_provider_exception(self):
        p1 = _FakeProvider("github", ["github_get_pr"], raise_on_dispatch=RuntimeError("boom"))
        registry = ProviderRegistry([p1])
        result = registry.dispatch("github_get_pr", {"number": 1})
        self.assertIn("github tool error", result)
        self.assertIn("boom", result)


if __name__ == "__main__":
    unittest.main()
