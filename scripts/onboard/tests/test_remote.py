import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.onboard import onboard
from scripts.onboard.tests.test_onboard import YAB_ORIGIN, git, make_repo

NEW_URL = "https://github.com/me/proj"


def origin(root):
    return subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = make_repo(self.tmp.name, origin=YAB_ORIGIN)
        self.gh_calls = []

    def fake_gh(self, *args, fail=False):
        def gh(*a):
            self.gh_calls.append(a)
            if fail:
                raise onboard.OnboardError("gh repo create failed: name already exists")
            return NEW_URL if a[:2] == ("repo", "view") else ""
        return mock.patch.object(onboard, "_gh", side_effect=gh)

    def test_create_private_by_default_and_repoints_origin(self):
        with self.fake_gh():
            result = onboard.remote(self.root, create="proj")
        self.assertEqual(self.gh_calls[0], ("repo", "create", "proj", "--private"))
        self.assertEqual(self.gh_calls[1], ("repo", "view", "proj", "--json", "url", "--jq", ".url"))
        self.assertEqual(origin(self.root), NEW_URL + ".git")
        self.assertEqual(result, {"origin": NEW_URL + ".git", "created": "proj"})

    def test_create_public(self):
        with self.fake_gh():
            onboard.remote(self.root, create="me/proj", public=True)
        self.assertEqual(self.gh_calls[0], ("repo", "create", "me/proj", "--public"))

    def test_create_adds_origin_when_there_is_none(self):
        git(self.root, "remote", "remove", "origin")
        with self.fake_gh():
            onboard.remote(self.root, create="proj")
        self.assertEqual(origin(self.root), NEW_URL + ".git")

    def test_gh_failure_leaves_origin_alone(self):
        with self.fake_gh(fail=True), self.assertRaises(onboard.OnboardError):
            onboard.remote(self.root, create="proj")
        self.assertEqual(origin(self.root), YAB_ORIGIN)

    def test_view_failure_after_create_points_at_url(self):
        def gh(*a):
            if a[:2] == ("repo", "view"):
                raise onboard.OnboardError("gh repo view failed")
            return ""
        with mock.patch.object(onboard, "_gh", side_effect=gh):
            with self.assertRaisesRegex(onboard.OnboardError, "created proj .*--url"):
                onboard.remote(self.root, create="proj")
        self.assertEqual(origin(self.root), YAB_ORIGIN)

    def test_invalid_names_rejected_before_gh_runs(self):
        for bad in ["", "a b", "-x", "../x", "o/n/x", "x/", "/x", "a" * 101]:
            with self.fake_gh(), self.assertRaises(onboard.Refused, msg=bad):
                onboard.remote(self.root, create=bad)
        self.assertEqual(self.gh_calls, [])

    def test_url_sets_origin(self):
        self.assertEqual(onboard.remote(self.root, url="git@github.com:me/proj.git")["origin"], "git@github.com:me/proj.git")
        self.assertEqual(origin(self.root), "git@github.com:me/proj.git")

    def test_url_rejects_yab_and_non_network_urls(self):
        for bad in [YAB_ORIGIN, "git@github.com:lutsenko-yuriy/yuriys-agentic-boyz.git", "/tmp/x", "file:///tmp/x", "-u"]:
            with self.assertRaises(onboard.Refused, msg=bad):
                onboard.remote(self.root, url=bad)
        self.assertEqual(origin(self.root), YAB_ORIGIN)

    def test_none_removes_origin_and_is_idempotent(self):
        self.assertEqual(onboard.remote(self.root, none=True), {"origin": None, "created": None})
        self.assertEqual(origin(self.root), "")
        self.assertEqual(onboard.remote(self.root, none=True), {"origin": None, "created": None})

    def test_refuses_once_origin_is_not_yab(self):
        git(self.root, "remote", "set-url", "origin", "https://github.com/someone/else.git")
        with self.fake_gh():
            for kwargs in ({"create": "proj"}, {"url": NEW_URL}, {"none": True}):
                with self.assertRaises(onboard.Refused, msg=kwargs):
                    onboard.remote(self.root, **kwargs)
        self.assertEqual(self.gh_calls, [])
        self.assertEqual(origin(self.root), "https://github.com/someone/else.git")

    def test_cli(self):
        root = str(self.root)
        self.assertEqual(onboard.main(["--root", root, "remote", "--none"]), 0)
        self.assertEqual(onboard.main(["--root", root, "remote"]), 3)
        self.assertEqual(onboard.main(["--root", root, "remote", "--none", "--url", NEW_URL]), 3)
        self.assertEqual(onboard.main(["--root", root, "remote", "--url", NEW_URL, "--public"]), 3)
        git(self.root, "remote", "add", "origin", "https://github.com/someone/else.git")
        self.assertEqual(onboard.main(["--root", root, "remote", "--none"]), 1)


if __name__ == "__main__":
    unittest.main()
