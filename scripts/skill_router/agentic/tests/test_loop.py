import io
import unittest
from unittest.mock import MagicMock, patch

from skill_router.agentic.loop import chat_completion_with_tools
from skill_router.agentic.registry import ProviderRegistry


def _make_completion_response(content=None, tool_calls=None, finish_reason=None):
    msg = {"role": "assistant"}
    if content is not None:
        msg["content"] = content
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    if finish_reason is None:
        finish_reason = "tool_calls" if tool_calls else "stop"
    return {"choices": [{"message": msg, "finish_reason": finish_reason}]}


class _FakeProvider:
    def __init__(self, group_name, tool_names, dispatch_result="ok"):
        self.group_name = group_name
        self._tool_names = tool_names
        self._dispatch_result = dispatch_result
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
        return self._dispatch_result

    def validate(self):
        return None


def _empty_registry():
    return ProviderRegistry([])


class TestChatCompletionWithTools(unittest.TestCase):

    def test_final_answer_printed_and_returns_true(self):
        response = _make_completion_response(content="All done.")
        with patch("urllib.request.urlopen") as mock_open:
            with patch("json.load", return_value=response):
                mock_resp = MagicMock()
                mock_resp.__enter__ = lambda s: s
                mock_resp.__exit__ = MagicMock(return_value=False)
                mock_open.return_value = mock_resp
                with patch("sys.stdout", new_callable=io.StringIO) as out:
                    result = chat_completion_with_tools("model", "prompt", _empty_registry())
        self.assertTrue(result)
        self.assertIn("All done.", out.getvalue())

    def test_tool_call_dispatched_then_final_answer(self):
        tool_call_resp = _make_completion_response(
            tool_calls=[{
                "id": "tc1",
                "function": {"name": "read_file", "arguments": '{"path": "foo.txt"}'},
            }],
        )
        final_resp = _make_completion_response(content="Done after tool.")

        provider = _FakeProvider("files", ["read_file"], dispatch_result="file content")
        registry = ProviderRegistry([provider])

        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with patch("json.load", side_effect=[tool_call_resp, final_resp]):
                with patch("sys.stdout", new_callable=io.StringIO):
                    result = chat_completion_with_tools("model", "prompt", registry)
        self.assertTrue(result)
        self.assertEqual(provider.dispatch_calls, [("read_file", {"path": "foo.txt"})])

    def test_network_error_returns_false(self):
        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            result = chat_completion_with_tools("model", "prompt", _empty_registry())
        self.assertFalse(result)

    def test_empty_choices_returns_false(self):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with patch("json.load", return_value={"choices": []}):
                result = chat_completion_with_tools("model", "prompt", _empty_registry())
        self.assertFalse(result)

    def test_max_turns_exceeded_returns_false(self):
        tool_call_resp = _make_completion_response(
            tool_calls=[{
                "id": "tc1",
                "function": {"name": "read_file", "arguments": '{"path": "x"}'},
            }],
        )
        provider = _FakeProvider("files", ["read_file"], dispatch_result="result")
        registry = ProviderRegistry([provider])

        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with patch("json.load", return_value=tool_call_resp):
                result = chat_completion_with_tools("model", "prompt", registry)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
