"""Cutover wiring (HAB-278 WU7): the committed hook settings and the .yab-template sentinel.

Readers of .claude/settings.json: Claude Code (hooks), this file. Readers of .yab-template: onboard._template_mode
(check, apply, mark), test_skill.make_clone (writes its own), this file.

State table (what must hold for the committed files):
    settings.json   | events SessionStart/UserPromptExpansion/PreToolUse each present exactly once
                    | command = "${CLAUDE_PROJECT_DIR}/scripts/onboard/gate.sh <Event>" (event == its own row)
                    | timeout >= 4 and > gate.sh watchdog default; gate.sh tracked executable
    .yab-template   | parses to YAB_REPO; with origin YAB -> template mode, with another origin -> not
"""

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.onboard import onboard
from scripts.onboard.tests import YAB_REPOSITORY, template_only, template_state_expected
from scripts.onboard.tests.test_onboard import YAB_SENTINEL

ROOT = Path(__file__).resolve().parents[3]
SETTINGS = ROOT / ".claude" / "settings.json"
EVENTS = ("SessionStart", "UserPromptExpansion", "PreToolUse")
COMMAND_RE = re.compile(r'^"\$\{CLAUDE_PROJECT_DIR\}/scripts/onboard/gate\.sh" (\w+)$')


def gate_rows():
    hooks = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]
    rows = []
    for event, groups in hooks.items():
        for group in groups:
            for hook in group["hooks"]:
                rows.append((event, group, hook))
    return rows


class SettingsWiringTests(unittest.TestCase):
    def test_all_three_events_wired_once(self):
        self.assertEqual(sorted(EVENTS), sorted(e for e, _, _ in gate_rows()))

    def test_each_row_passes_its_own_event_to_gate_sh(self):
        for event, _, hook in gate_rows():
            self.assertEqual("command", hook["type"])
            m = COMMAND_RE.match(hook["command"])
            self.assertIsNotNone(m, hook["command"])
            self.assertEqual(event, m.group(1))

    def test_timeout_above_watchdog(self):
        sh = (ROOT / "scripts/onboard/gate.sh").read_text(encoding="utf-8")
        deadline = float(re.search(r'YAB_GATE_DEADLINE:-(\d+(?:\.\d+)?)', sh).group(1))
        for event, _, hook in gate_rows():
            self.assertGreaterEqual(hook["timeout"], 4, event)
            self.assertGreater(hook["timeout"], deadline, event)

    def test_session_start_only_on_startup_and_others_unfiltered(self):
        for event, group, _ in gate_rows():
            if event == "SessionStart":
                self.assertEqual("startup", group.get("matcher"))
            else:
                self.assertIn(group.get("matcher", ""), ("", "*"), event)

    def test_gate_sh_is_tracked_executable(self):
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-s", "scripts/onboard/gate.sh"],
                             capture_output=True, text=True, check=True).stdout
        self.assertTrue(out.startswith("100755"), out)

    def test_settings_json_tracked_and_local_ignored(self):
        def ignored(p):
            return subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", p]).returncode == 0
        self.assertFalse(ignored(".claude/settings.json"))
        self.assertTrue(ignored(".claude/settings.local.json"))


class SentinelTests(unittest.TestCase):
    @template_only
    def test_committed_sentinel_names_yab(self):
        text = (ROOT / ".yab-template").read_text(encoding="utf-8")
        fields = dict(ln.split("=", 1) for ln in text.splitlines() if "=" in ln)
        self.assertEqual(onboard.YAB_REPO, fields["repo"].strip())

    def _mode(self, origin):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "-C", tmp, "init", "-q"], check=True)
            subprocess.run(["git", "-C", tmp, "remote", "add", "origin", origin], check=True)
            (Path(tmp) / ".yab-template").write_text(YAB_SENTINEL, encoding="utf-8")
            return onboard._template_mode(Path(tmp), [])

    def test_template_mode_only_with_yab_origin(self):
        self.assertTrue(self._mode("https://github.com/%s.git" % onboard.YAB_REPO))
        self.assertFalse(self._mode("https://github.com/someone/else.git"))


class TemplateGuardTests(unittest.TestCase):
    def _expected(self, sentinel, env):
        with tempfile.TemporaryDirectory() as tmp:
            if sentinel:
                (Path(tmp) / ".yab-template").write_text(YAB_SENTINEL, encoding="utf-8")
            return template_state_expected(Path(tmp), env)

    def test_sentinel_present_runs_template_tests(self):
        self.assertTrue(self._expected(True, {}))

    def test_onboarded_repo_outside_yab_ci_skips(self):
        self.assertFalse(self._expected(False, {}))
        self.assertFalse(self._expected(False, {"GITHUB_REPOSITORY": "someone/else"}))

    def test_missing_sentinel_in_yab_ci_does_not_skip(self):
        self.assertTrue(self._expected(False, {"GITHUB_REPOSITORY": YAB_REPOSITORY}))


if __name__ == "__main__":
    unittest.main()
