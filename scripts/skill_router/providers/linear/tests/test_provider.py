import json
import unittest
from unittest.mock import patch

from skill_router.providers.linear.provider import LinearProvider


class TestLinearProvider(unittest.TestCase):

    def test_validate_returns_none_when_api_key_set(self):
        p = LinearProvider(api_key="lin_api_test", project_id="proj")
        self.assertIsNone(p.validate())

    def test_validate_returns_error_when_no_api_key(self):
        p = LinearProvider(api_key=None, project_id="proj")
        err = p.validate()
        self.assertIsNotNone(err)
        self.assertIn("LINEAR_API_KEY", err)

    def test_handles_linear_tool_names(self):
        p = LinearProvider(api_key="x", project_id="y")
        self.assertTrue(p.handles("linear_list_issues"))
        self.assertTrue(p.handles("linear_get_issue"))
        self.assertTrue(p.handles("linear_update_issue_state"))
        self.assertTrue(p.handles("linear_create_comment"))
        self.assertFalse(p.handles("github_get_pr"))
        self.assertFalse(p.handles("read_file"))

    def test_dispatch_linear_list_issues(self):
        fake_nodes = [{"identifier": "HAB-1", "title": "T"}]
        with patch(
            "skill_router.providers.linear.provider._linear_graphql",
            return_value={"data": {"issues": {"nodes": fake_nodes}}},
        ) as mock_gql:
            p = LinearProvider(api_key="key", project_id="proj")
            result = p.dispatch("linear_list_issues", {})
        self.assertEqual(json.loads(result), fake_nodes)
        mock_gql.assert_called_once()


if __name__ == "__main__":
    unittest.main()
