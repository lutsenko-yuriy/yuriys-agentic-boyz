import unittest
from unittest.mock import MagicMock, patch

from skill_router.providers.files.provider import FilesProvider


class TestFilesProvider(unittest.TestCase):

    def test_handles_file_tool_names(self):
        p = FilesProvider()
        self.assertTrue(p.handles("read_file"))
        self.assertTrue(p.handles("write_file"))
        self.assertTrue(p.handles("run_bash"))
        self.assertFalse(p.handles("linear_list_issues"))
        self.assertFalse(p.handles("github_get_pr"))

    def test_dispatch_read_file(self):
        with patch("pathlib.Path.read_text", return_value="file contents") as mock_read:
            p = FilesProvider()
            result = p.dispatch("read_file", {"path": "foo.txt"})
        self.assertEqual(result, "file contents")
        mock_read.assert_called_once()

    def test_dispatch_write_file(self):
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch("pathlib.Path.write_text") as mock_write:
                p = FilesProvider()
                result = p.dispatch("write_file", {"path": "out/foo.txt", "content": "hello"})
        self.assertIn("out/foo.txt", result)
        mock_write.assert_called_once_with("hello")
        mock_mkdir.assert_called_once()

    def test_dispatch_run_bash(self):
        fake_result = MagicMock()
        fake_result.stdout = "hello\n"
        fake_result.stderr = ""
        with patch("subprocess.run", return_value=fake_result) as mock_sub:
            p = FilesProvider()
            result = p.dispatch("run_bash", {"command": "echo hello"})
        self.assertIn("hello", result)
        mock_sub.assert_called_once()

    def test_dispatch_unknown_tool_returns_error(self):
        p = FilesProvider()
        result = p.dispatch("nonexistent", {})
        self.assertIn("Unknown files tool", result)


if __name__ == "__main__":
    unittest.main()
