import unittest
from unittest.mock import patch

from skill_router.core.frontmatter import read_frontmatter
from skill_router.agentic.constants import MAX_TOOL_TURNS
from .fixtures import (
    SKILL_CONTENT_PLAIN,
    SKILL_CONTENT_NEEDS_MCP,
    SKILL_CONTENT_WITH_CONTEXT,
    SKILL_CONTENT_WITH_TOOLS,
    SKILL_CONTENT_NO_FM,
)


class TestReadFrontmatter(unittest.TestCase):

    def _parse(self, content):
        with patch("pathlib.Path.read_text", return_value=content):
            return read_frontmatter("fake/SKILL.md")

    def test_parses_effort_and_reasoning(self):
        effort, reasoning, _, _, _, _, _ = self._parse(SKILL_CONTENT_PLAIN)
        self.assertEqual(effort, "RAPID")
        self.assertEqual(reasoning, "MECHANICAL")

    def test_needs_session_tools_false_by_default(self):
        _, _, needs_session_tools, _, _, _, _ = self._parse(SKILL_CONTENT_PLAIN)
        self.assertFalse(needs_session_tools)

    def test_needs_session_tools_true_when_set(self):
        _, _, needs_session_tools, _, _, _, _ = self._parse(SKILL_CONTENT_NEEDS_MCP)
        self.assertTrue(needs_session_tools)

    def test_context_none_by_default(self):
        _, _, _, context, _, _, _ = self._parse(SKILL_CONTENT_PLAIN)
        self.assertIsNone(context)

    def test_context_parsed_when_set(self):
        _, _, _, context, _, _, _ = self._parse(SKILL_CONTENT_WITH_CONTEXT)
        self.assertEqual(context, "linear")

    def test_tools_empty_by_default(self):
        _, _, _, _, tools, _, _ = self._parse(SKILL_CONTENT_PLAIN)
        self.assertEqual(tools, [])

    def test_tools_parsed_when_set(self):
        _, _, _, _, tools, _, _ = self._parse(SKILL_CONTENT_WITH_TOOLS)
        self.assertEqual(tools, ["linear", "github"])

    def test_max_turns_defaults_to_constant(self):
        _, _, _, _, _, max_turns, _ = self._parse(SKILL_CONTENT_PLAIN)
        self.assertEqual(max_turns, MAX_TOOL_TURNS)

    def test_max_turns_parsed_when_set(self):
        content = "---\neffort: RAPID\nreasoning: MECHANICAL\nmax_turns: 60\n---\nDo the thing.\n"
        _, _, _, _, _, max_turns, _ = self._parse(content)
        self.assertEqual(max_turns, 60)

    def test_body_excludes_frontmatter(self):
        _, _, _, _, _, _, body = self._parse(SKILL_CONTENT_PLAIN)
        self.assertEqual(body, "Do the thing.\n")

    def test_no_frontmatter_returns_none_fields(self):
        effort, reasoning, needs_session_tools, context, tools, max_turns, body = self._parse(SKILL_CONTENT_NO_FM)
        self.assertIsNone(effort)
        self.assertIsNone(reasoning)
        self.assertFalse(needs_session_tools)
        self.assertIsNone(context)
        self.assertEqual(tools, [])
        self.assertEqual(max_turns, MAX_TOOL_TURNS)
        self.assertEqual(body, SKILL_CONTENT_NO_FM)


if __name__ == "__main__":
    unittest.main()
