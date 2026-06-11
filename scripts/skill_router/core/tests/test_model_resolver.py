import unittest
from unittest.mock import patch

from skill_router.core.model_resolver import normalize_model_name, lookup_lmstudio_model
from .fixtures import TIERS_MD_WITH_LMSTUDIO


class TestNormalizeModelName(unittest.TestCase):

    def test_strips_parenthetical_quantization(self):
        self.assertEqual(normalize_model_name("qwen/qwen3-8b (MLX, 4-bit)"), "qwen/qwen3-8b")

    def test_strips_after_first_space(self):
        self.assertEqual(normalize_model_name("mistralai/devstral-small 4bit"), "mistralai/devstral-small")

    def test_lowercases(self):
        self.assertEqual(normalize_model_name("Qwen/Qwen3-8B"), "qwen/qwen3-8b")

    def test_plain_name_unchanged(self):
        self.assertEqual(normalize_model_name("qwen/qwen3-8b"), "qwen/qwen3-8b")

    def test_strips_leading_trailing_whitespace(self):
        self.assertEqual(normalize_model_name("  qwen/qwen3-8b  "), "qwen/qwen3-8b")


class TestLookupLmstudioModel(unittest.TestCase):

    def _lookup(self, effort, reasoning, tiers_content=TIERS_MD_WITH_LMSTUDIO):
        with patch("pathlib.Path.read_text", return_value=tiers_content):
            return lookup_lmstudio_model(effort, reasoning)

    def test_returns_model_for_lm_studio_alias(self):
        model = self._lookup("RAPID", "MECHANICAL")
        self.assertEqual(model, "qwen/qwen3-8b (MLX, 4-bit)")

    def test_returns_none_for_non_lm_studio_alias(self):
        model = self._lookup("THOROUGH", "ARCHITECTURAL")
        self.assertIsNone(model)

    def test_returns_none_for_missing_combination(self):
        model = self._lookup("FOCUSED", "TACTICAL")
        self.assertIsNone(model)

    def test_returns_none_when_file_missing(self):
        with patch("pathlib.Path.read_text", side_effect=FileNotFoundError):
            model = lookup_lmstudio_model("RAPID", "MECHANICAL")
        self.assertIsNone(model)

    def test_returns_none_when_section_missing(self):
        model = self._lookup("RAPID", "MECHANICAL", tiers_content="no active mapping here")
        self.assertIsNone(model)


if __name__ == "__main__":
    unittest.main()
