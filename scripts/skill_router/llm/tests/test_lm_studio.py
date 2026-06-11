import io
import unittest
from unittest.mock import MagicMock, patch

from skill_router.llm.lm_studio import _auth_headers, model_loaded, stream_completion


class TestAuthHeaders(unittest.TestCase):

    def test_returns_empty_dict_when_no_token(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(_auth_headers(), {})

    def test_returns_bearer_header_when_token_set(self):
        with patch.dict("os.environ", {"LM_API_TOKEN": "sk-lm-test123"}):
            self.assertEqual(
                _auth_headers(),
                {"Authorization": "Bearer sk-lm-test123"},
            )


class TestModelLoaded(unittest.TestCase):

    def _run(self, model_name, loaded_ids):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen") as mock_urlopen:
            with patch("json.load", return_value={"data": [{"id": mid} for mid in loaded_ids]}):
                mock_urlopen.return_value = mock_resp
                return model_loaded(model_name)

    def test_exact_base_name_match(self):
        self.assertTrue(self._run("qwen/qwen3-8b (MLX, 4-bit)", ["qwen/qwen3-8b"]))

    def test_mlx_suffix_variant_matches(self):
        self.assertTrue(self._run("qwen/qwen3-8b (MLX, 4-bit)", ["qwen/qwen3-8b-mlx"]))

    def test_no_match_returns_false(self):
        self.assertFalse(self._run("qwen/qwen3-8b (MLX, 4-bit)", ["mistralai/devstral-small"]))

    def test_unreachable_lm_studio_returns_false(self):
        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            self.assertFalse(model_loaded("qwen/qwen3-8b"))


class TestStreamCompletion(unittest.TestCase):

    def _make_sse_lines(self, chunks, done=True):
        import json
        lines = []
        for text in chunks:
            payload = json.dumps({"choices": [{"delta": {"content": text}}]})
            lines.append(f"data: {payload}\n".encode())
        if done:
            lines.append(b"data: [DONE]\n")
        return lines

    def test_streams_content_to_stdout(self):
        lines = self._make_sse_lines(["Hello", ", ", "world"])
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.__iter__ = MagicMock(return_value=iter(lines))
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                result = stream_completion("qwen/qwen3-8b", "prompt")
        self.assertTrue(result)
        self.assertIn("Hello", mock_out.getvalue())
        self.assertIn("world", mock_out.getvalue())

    def test_returns_false_on_network_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            result = stream_completion("qwen/qwen3-8b", "prompt")
        self.assertFalse(result)

    def test_tolerates_malformed_chunks(self):
        lines = [b"data: not-json\n", b"data: [DONE]\n"]
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.__iter__ = MagicMock(return_value=iter(lines))
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = stream_completion("qwen/qwen3-8b", "prompt")
        self.assertTrue(result)

    def test_skips_non_data_lines(self):
        lines = [b"event: ping\n", b"data: [DONE]\n"]
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.__iter__ = MagicMock(return_value=iter(lines))
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = stream_completion("qwen/qwen3-8b", "prompt")
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
