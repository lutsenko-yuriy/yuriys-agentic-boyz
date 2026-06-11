import unittest
from unittest.mock import MagicMock, patch

from skill_router.providers.github.provider import GithubProvider


class TestGithubProvider(unittest.TestCase):

    def test_handles_github_tool_names(self):
        p = GithubProvider()
        self.assertTrue(p.handles("github_get_pr"))
        self.assertTrue(p.handles("github_get_pr_diff"))
        self.assertTrue(p.handles("github_create_pr_comment"))
        self.assertTrue(p.handles("github_create_pr_review_comment"))
        self.assertTrue(p.handles("github_merge_pr"))
        self.assertFalse(p.handles("linear_list_issues"))
        self.assertFalse(p.handles("read_file"))

    def test_dispatch_get_pr_diff_truncates_long_output(self):
        long_diff = "x" * 200_000
        fake_result = MagicMock()
        fake_result.stdout = long_diff
        fake_result.stderr = ""
        with patch("subprocess.run", return_value=fake_result):
            p = GithubProvider()
            result = p.dispatch("github_get_pr_diff", {"number": 42})
        self.assertTrue(result.endswith("[truncated]"))
        self.assertLess(len(result), len(long_diff))

    def test_dispatch_unknown_tool_returns_error(self):
        p = GithubProvider()
        result = p.dispatch("github_nonexistent", {})
        self.assertIn("Unknown GitHub tool", result)


if __name__ == "__main__":
    unittest.main()
