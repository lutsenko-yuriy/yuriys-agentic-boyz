import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from scripts.onboard import gate, onboard

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_SH = REPO_ROOT / "scripts" / "onboard" / "gate.sh"
NEEDS = "Onboarding required"


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def make_repo(parent, name="repo"):
    root = Path(parent) / name
    root.mkdir()
    git(root, "init", "-q")
    (root / "docs").mkdir()
    return root.resolve()


def mark(root):
    marker = onboard.marker_path(root)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("onboarded=x\n")


def pre(root, tool, tool_input, **extra):
    d = {"hook_event_name": "PreToolUse", "cwd": str(root), "tool_name": tool, "tool_input": tool_input}
    d.update(extra)
    return d


def run(payload, event=None):
    return gate.run(payload if isinstance(payload, str) else json.dumps(payload), event)


def decision(result):
    """None for pass-through (exit 0, no output); "deny" for a deny JSON."""
    code, out, _ = result
    assert code == 0, result
    if not out:
        return None
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = make_repo(self.tmp)
        self.project_dir(self.root)

    def project_dir(self, path):
        """Set (or, with None, unset) CLAUDE_PROJECT_DIR for this test only; the original value is restored."""
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        if path is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = str(path)


class OnboardedIsNoOp(Base):
    def test_every_event_and_tool_is_silent(self):
        mark(self.root)
        cases = [
            {"hook_event_name": "SessionStart", "cwd": str(self.root)},
            {"hook_event_name": "UserPromptExpansion", "cwd": str(self.root), "expansion_type": "slash_command",
             "command_name": "plan", "command_source": "projectSettings"},
            pre(self.root, "Bash", {"command": "git commit -m x"}),
            pre(self.root, "Agent", {}),
            pre(self.root, "Write", {"file_path": str(self.root / "x.py")}),
            pre(self.root, "mcp__linear__save_issue", {}),
            {"hook_event_name": "Whatever", "cwd": str(self.root)},
        ]
        for case in cases:
            self.assertEqual(run(case), (0, "", ""), case)

    def test_malformed_stdin_is_silent_when_onboarded(self):
        mark(self.root)
        self.project_dir(self.root)
        self.assertEqual(run("not json", "PreToolUse"), (0, "", ""))

    def test_marker_shared_with_worktree(self):
        git(self.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
        wt = Path(self.tmp) / "wt"
        git(self.root, "worktree", "add", "-q", str(wt), "-b", "b")
        mark(self.root)
        self.project_dir(None)
        self.assertEqual(run(pre(wt.resolve(), "Agent", {})), (0, "", ""))


class SessionStartAndPrompt(Base):
    def test_session_start_injects_context(self):
        code, out, _ = run({"hook_event_name": "SessionStart", "cwd": str(self.root), "source": "startup"})
        self.assertEqual(code, 0)
        hso = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "SessionStart")
        self.assertIn("/onboard", hso["additionalContext"])

    def expansion(self, name, source="projectSettings", kind="slash_command"):
        return run({"hook_event_name": "UserPromptExpansion", "cwd": str(self.root), "expansion_type": kind,
                    "command_name": name, "command_source": source})

    def test_onboard_allowed_any_source(self):
        for src in ("projectSettings", "userSettings", "plugin"):
            self.assertEqual(self.expansion("onboard", src), (0, "", ""))

    def test_other_custom_commands_blocked_with_exit_2(self):
        for name in ("plan", "implement", "onboard2", "Onboard", ""):
            code, out, err = self.expansion(name)
            self.assertEqual((code, out), (gate.BLOCK_EXIT, ""), name)
            self.assertIn(NEEDS, err)

    def test_builtin_source_allowed_and_non_slash_expansion_ignored(self):
        self.assertEqual(self.expansion("mcp", "builtin"), (0, "", ""))
        self.assertEqual(self.expansion("plan", kind="mcp_prompt"), (0, "", ""))


class PreToolUseTools(Base):
    def test_skill(self):
        self.assertIsNone(decision(run(pre(self.root, "Skill", {"skill": "onboard"}))))
        for bad in ({"skill": "plan"}, {"skill": "onboard2"}, {}, {"skill": None}):
            self.assertEqual(decision(run(pre(self.root, "Skill", bad))), "deny", bad)

    def test_agent_denied_including_subagent_calls(self):
        self.assertEqual(decision(run(pre(self.root, "Agent", {"prompt": "x"}))), "deny")
        self.assertEqual(decision(run(pre(self.root, "Agent", {}, agent_id="a1"))), "deny")

    def test_bash_uses_policy(self):
        self.assertIsNone(decision(run(pre(self.root, "Bash", {"command": "git log | head"}))))
        for cmd in ("git commit -m x", "find . -delete", "cat a > b", "script -q /dev/null sh", ""):
            self.assertEqual(decision(run(pre(self.root, "Bash", {"command": cmd}))), "deny", cmd)
        for bad in ({}, {"command": 5}, {"command": None}):
            self.assertEqual(decision(run(pre(self.root, "Bash", bad))), "deny", bad)

    def test_bash_deny_reason_carries_policy_reason(self):
        _, out, _ = run(pre(self.root, "Bash", {"command": "git commit -m x"}))
        reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("/onboard", reason)
        self.assertIn("git", reason)

    def test_mcp_verbs(self):
        for ok in ("mcp__linear__get_issue", "mcp__linear__list_issues", "mcp__x__search_documentation",
                   "mcp__linear__extract_images"):
            self.assertIsNone(decision(run(pre(self.root, "mcp__x__y".replace("x__y", ok[5:]), {}))), ok)
        for bad in ("mcp__linear__save_issue", "mcp__linear__create_attachment", "mcp__linear__delete_comment",
                    "mcp__linear__update_diff", "mcp__linear__merge_diff", "mcp__linear__getissue",
                    "mcp__linear", "mcp__get_issue", "mcp__linear__list_x__save_y", "mcp__s__x__get_y", "mcp__s__get_x__save_y", "mcp__"):
            self.assertEqual(decision(run(pre(self.root, bad, {}))), "deny", bad)

    def test_read_only_builtins_pass_and_unknown_tools_denied(self):
        for tool in ("Read", "Glob", "Grep", "WebFetch", "AskUserQuestion", "ToolSearch"):
            self.assertIsNone(decision(run(pre(self.root, tool, {}))), tool)
        for tool in ("SomeNewTool", "KillShell", "REPL", "", "read"):
            self.assertEqual(decision(run(pre(self.root, tool, {}))), "deny", tool)

    def test_never_emits_allow(self):
        tools = [("Skill", {"skill": "onboard"}), ("Read", {}), ("Bash", {"command": "ls"}),
                 ("mcp__a__get_b", {}), ("Write", {"file_path": "AGENTS.md"})]
        for tool, inp in tools:
            code, out, _ = run(pre(self.root, tool, inp))
            self.assertEqual((code, out), (0, ""), tool)

    def test_malformed_tool_call_denied(self):
        for payload in ({"hook_event_name": "PreToolUse", "cwd": str(self.root), "tool_name": "Read"},
                        {"hook_event_name": "PreToolUse", "cwd": str(self.root), "tool_input": {}},
                        {"hook_event_name": "PreToolUse", "cwd": str(self.root), "tool_name": 3, "tool_input": {}}):
            self.assertEqual(decision(run(payload)), "deny", payload)


class WritePaths(Base):
    def write(self, path, tool="Write", **extra):
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        return decision(run(pre(self.root, tool, {key: path}, **extra)))

    def test_every_bootstrap_path_allowed_absolute_and_relative(self):
        for rel in gate.BOOTSTRAP_PATHS:
            self.assertIsNone(self.write(str(self.root / rel)), rel)
            self.assertIsNone(self.write(rel), rel)

    def test_every_onboard_artifact_is_a_bootstrap_path(self):
        for rel in onboard.ARTIFACTS:
            self.assertIn(rel, gate.BOOTSTRAP_PATHS)
            self.assertIsNone(self.write(rel), rel)

    def test_new_onboard_artifact_flows_into_bootstrap_paths(self):
        with mock.patch.object(onboard, "ARTIFACTS", onboard.ARTIFACTS + ["docs/NEW_ARTIFACT.md"]):
            importlib.reload(gate)
            self.addCleanup(importlib.reload, gate)
            self.assertIn("docs/NEW_ARTIFACT.md", gate.BOOTSTRAP_PATHS)

    def test_all_write_tools_checked(self):
        for tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            self.assertIsNone(self.write("docs/TECH_STACK.md", tool), tool)
            self.assertEqual(self.write("docs/PRODUCT_SPEC.md", tool), "deny", tool)

    def test_other_paths_denied(self):
        for rel in ("docs/PRODUCT_SPEC.md", "scripts/x.py", ".claude/settings.json", "docs/TECH_STACK.md.bak",
                    "docs/TECH_STACK.md/x", "docs/tech_stack.md", "docs/knowledge/notes/X-1.md"):
            self.assertEqual(self.write(rel), "deny", rel)

    def test_bad_path_values(self):
        for bad in (None, "", "  ", 5, ["AGENTS.md"], "AGENTS.md\0x"):
            self.assertEqual(decision(run(pre(self.root, "Write", {"file_path": bad}))), "deny", bad)
        self.assertEqual(decision(run(pre(self.root, "Write", {}))), "deny")

    def test_dotdot_escape_and_dotdot_normalisation(self):
        self.assertEqual(self.write("../repo2/AGENTS.md"), "deny")
        self.assertEqual(self.write("docs/../../AGENTS.md"), "deny")
        self.assertIsNone(self.write("docs/../AGENTS.md"))
        self.assertIsNone(self.write("docs/./TECH_STACK.md"))

    def test_absolute_path_outside_repo(self):
        other = make_repo(self.tmp, "other")
        self.assertEqual(self.write(str(other / "AGENTS.md")), "deny")
        self.assertEqual(self.write("/etc/passwd"), "deny")

    def test_nonexistent_new_file_in_allowed_dir_is_allowed(self):
        self.assertFalse((self.root / "docs" / "TECH_STACK.md").exists())
        self.assertIsNone(self.write(str(self.root / "docs" / "TECH_STACK.md")))
        self.assertIsNone(self.write("skills/shared/pm-tool-mapping.md"))  # parent dirs do not exist yet

    def test_symlinked_file_escaping_repo_denied(self):
        outside = Path(self.tmp) / "outside.md"
        outside.write_text("x")
        os.symlink(str(outside), str(self.root / "AGENTS.md"))
        self.assertEqual(self.write("AGENTS.md"), "deny")
        self.assertEqual(self.write(str(outside)), "deny")

    def test_symlinked_dir_escaping_repo_denied(self):
        outside = Path(self.tmp) / "outdir"
        outside.mkdir()
        os.symlink(str(outside), str(self.root / "skills"))
        self.assertEqual(self.write("skills/shared/pm-tool-mapping.md"), "deny")

    def test_symlink_inside_repo_to_non_bootstrap_file_denied(self):
        (self.root / "secret.md").write_text("x")
        os.symlink(str(self.root / "secret.md"), str(self.root / "docs" / "TECH_STACK.md"))
        self.assertEqual(self.write("docs/TECH_STACK.md"), "deny")  # resolves to secret.md, not the bootstrap path

    def test_symlink_alias_of_bootstrap_file_denied(self):
        (self.root / "AGENTS.md").write_text("x")
        os.symlink(str(self.root / "AGENTS.md"), str(self.root / "alias.md"))
        self.assertIsNone(self.write("alias.md"))  # realpath is AGENTS.md itself: same file, same effect

    def test_root_resolved_through_symlinked_checkout(self):
        link = Path(self.tmp) / "link"
        os.symlink(str(self.root), str(link))
        self.project_dir(link)
        payload = pre(link, "Write", {"file_path": str(link / "AGENTS.md")})
        self.assertIsNone(decision(run(payload)))

    def test_relative_path_resolves_against_cwd_from_subdir(self):
        sub = self.root / "docs"
        payload = pre(sub, "Write", {"file_path": "TECH_STACK.md"})
        self.assertIsNone(decision(run(payload)))
        payload = pre(sub, "Write", {"file_path": "PRODUCT_SPEC.md"})
        self.assertEqual(decision(run(payload)), "deny")


class RootResolution(Base):
    """The root comes from CLAUDE_PROJECT_DIR (stable); the payload cwd follows Bash `cd` and only resolves paths."""

    def test_cwd_in_nested_repo_of_onboarded_root_stays_onboarded(self):
        mark(self.root)
        nested = make_repo(self.root, "sub")
        self.assertEqual(run(pre(nested, "Write", {"file_path": str(self.root / "x.py")})), (0, "", ""))

    def test_cwd_in_non_git_dir_does_not_lock_out(self):
        mark(self.root)
        plain = Path(self.tmp) / "plain"
        plain.mkdir()
        self.assertEqual(run(pre(plain, "Bash", {"command": "git commit -m x"})), (0, "", ""))

    def test_unonboarded_root_not_bypassed_by_onboarded_nested_repo(self):
        nested = make_repo(self.root, "sub")
        mark(nested)
        self.assertEqual(decision(run(pre(nested, "Agent", {}))), "deny")

    def test_cwd_still_resolves_relative_write_paths(self):
        self.assertIsNone(decision(run(pre(self.root / "docs", "Write", {"file_path": "TECH_STACK.md"}))))
        nested = make_repo(self.root, "sub")
        self.assertEqual(decision(run(pre(nested, "Write", {"file_path": "AGENTS.md"}))), "deny")

    def test_no_git_repo_denies_with_git_init_hint(self):
        plain = Path(self.tmp) / "plain"
        plain.mkdir()
        self.project_dir(plain)
        with mock.patch("os.getcwd", return_value=str(plain)):
            code, out, _ = run(pre(plain, "Read", {"file_path": "x"}))
        self.assertEqual("deny", decision((code, out, "")))
        reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("not a git repository", reason)
        self.assertIn("git init", reason)
        self.assertIn("separate terminal", reason)
        self.assertIn("git init && git add -A && git commit", reason)
        # SessionStart and UserPromptExpansion still fail open
        with mock.patch("os.getcwd", return_value=str(plain)):
            self.assertEqual((0, "", ""), run({"hook_event_name": "SessionStart", "cwd": str(plain)}))

    def test_fallbacks_when_project_dir_unset_or_invalid(self):
        self.project_dir(None)
        self.assertEqual(decision(run(pre(self.root, "Agent", {}))), "deny")  # payload cwd
        with mock.patch("os.getcwd", return_value=str(self.root)):
            payload = pre(self.root, "Agent", {})
            del payload["cwd"]
            self.assertEqual(decision(run(payload)), "deny")  # process cwd


class AdopterSetup(Base):
    def test_renamed_remotes_do_not_matter_to_gating(self):
        git(self.root, "remote", "add", "upstream", "https://github.com/lutsenko-yuriy/yuriys-agentic-boyz.git")
        git(self.root, "remote", "add", "origin", "https://github.com/me/mine.git")
        self.assertEqual(decision(run(pre(self.root, "Agent", {}))), "deny")
        mark(self.root)
        self.assertEqual(run(pre(self.root, "Agent", {})), (0, "", ""))


class FailureSemantics(Base):
    def test_malformed_json_fallback_event(self):
        self.project_dir(self.root)
        self.assertEqual(decision(run("{nope", "PreToolUse")), "deny")
        self.assertEqual(decision(run("", "PreToolUse")), "deny")
        self.assertEqual(decision(run("[]", "PreToolUse")), "deny")
        self.assertEqual(run("{nope", "SessionStart"), (0, "", ""))
        self.assertEqual(run("{nope", "UserPromptExpansion"), (0, "", ""))
        self.assertEqual(run("{nope")[0], gate.BLOCK_EXIT)  # no event at all: fail closed

    def test_unknown_event_is_noop(self):
        self.assertEqual(run({"hook_event_name": "Stop", "cwd": str(self.root)}), (0, "", ""))

    def test_not_a_git_repo_follows_per_event_rule(self):
        plain = Path(self.tmp) / "plain"
        plain.mkdir()
        self.project_dir(None)
        with mock.patch("os.getcwd", return_value=str(plain)):
            self.assertEqual(decision(run(pre(plain, "Read", {}))), "deny")
            self.assertEqual(run({"hook_event_name": "SessionStart", "cwd": str(plain)}), (0, "", ""))
            self.assertEqual(run({"hook_event_name": "UserPromptExpansion", "cwd": str(plain),
                                  "expansion_type": "slash_command", "command_name": "plan"}), (0, "", ""))

    def test_internal_exception_fails_per_event(self):
        orig = gate.decide
        gate.decide = lambda *a, **k: 1 / 0
        self.addCleanup(setattr, gate, "decide", orig)
        self.assertEqual(decision(run(pre(self.root, "Read", {}))), "deny")
        self.assertEqual(run({"hook_event_name": "SessionStart", "cwd": str(self.root)}), (0, "", ""))


class EnvHygiene(unittest.TestCase):
    def test_tests_restore_a_preexisting_project_dir(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "/sentinel"}):
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(FailureSemantics)
            unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
            self.assertEqual(os.environ.get("CLAUDE_PROJECT_DIR"), "/sentinel")


class GitTimeout(Base):
    def test_gate_git_calls_use_a_short_timeout(self):
        seen = []
        real_root, real_marker = onboard.repo_root, onboard.marker_path
        with mock.patch.object(onboard, "repo_root", lambda *a, **k: (seen.append(k.get("timeout")), real_root(*a, **k))[1]), \
                mock.patch.object(onboard, "marker_path", lambda *a, **k: (seen.append(k.get("timeout")), real_marker(*a, **k))[1]):
            run(pre(self.root, "Read", {}))
        self.assertEqual(len(seen), 2)
        for t in seen:
            self.assertTrue(t is not None and t <= 2, seen)


class WrapperTests(Base):
    """gate.sh must turn any gate.py failure into the per-event rule (Claude Code fails open except on exit 2)."""

    def sh(self, event, payload, python=None, gate_py=None, deadline=None):
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(self.root)
        env["YAB_GATE_PYTHON"] = python or sys.executable
        if deadline:
            env["YAB_GATE_DEADLINE"] = deadline
        script = GATE_SH
        if gate_py is not None:  # a copy of the wrapper next to a fake gate.py ("" = no gate.py at all)
            d = Path(self.tmp) / "fake"
            d.mkdir(exist_ok=True)
            shutil.copy(str(GATE_SH), str(d / "gate.sh"))
            if gate_py:
                (d / "gate.py").write_text(gate_py)
            script = d / "gate.sh"
        args = [str(script)] + ([event] if event is not None else [])
        p = subprocess.run(args, input=payload if isinstance(payload, str) else json.dumps(payload),
                           capture_output=True, text=True, env=env)
        return p.returncode, p.stdout, p.stderr

    def test_passthrough_deny_and_allow(self):
        code, out, _ = self.sh("PreToolUse", pre(self.root, "Agent", {}))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(self.sh("PreToolUse", pre(self.root, "Read", {})), (0, "", ""))
        mark(self.root)
        self.assertEqual(self.sh("PreToolUse", pre(self.root, "Agent", {})), (0, "", ""))

    def test_prompt_block_exit_2_passes_through(self):
        code, out, err = self.sh("UserPromptExpansion", {
            "hook_event_name": "UserPromptExpansion", "cwd": str(self.root), "expansion_type": "slash_command",
            "command_name": "plan", "command_source": "projectSettings"})
        self.assertEqual((code, out), (2, ""))
        self.assertIn(NEEDS, err)

    def test_crashing_gate_py(self):
        crash = "raise RuntimeError('boom')\n"
        self.assertEqual(self.sh("PreToolUse", {}, gate_py=crash)[0], 2)
        self.assertEqual(self.sh("SessionStart", {}, gate_py=crash), (0, "", ""))
        self.assertEqual(self.sh("UserPromptExpansion", {}, gate_py=crash), (0, "", ""))
        self.assertEqual(self.sh(None, {}, gate_py=crash)[0], 2)
        self.assertEqual(self.sh("Bogus", {}, gate_py=crash)[0], 2)

    def test_missing_gate_py_does_not_lock_out_onboard(self):
        # CPython itself exits 2 when it cannot open the script; that must not be mistaken for a gate block.
        self.assertEqual(self.sh("UserPromptExpansion", {}, gate_py=""), (0, "", ""))
        self.assertEqual(self.sh("SessionStart", {}, gate_py=""), (0, "", ""))
        self.assertEqual(self.sh("PreToolUse", {}, gate_py="")[0], 2)

    def test_exit_2_from_gate_py_is_not_a_block(self):
        self.assertEqual(self.sh("UserPromptExpansion", {}, gate_py="import sys; sys.exit(2)\n"), (0, "", ""))
        self.assertEqual(self.sh("PreToolUse", {}, gate_py="import sys; sys.exit(2)\n")[0], 2)

    def test_gate_block_code_maps_to_exit_2(self):
        code, _, err = self.sh("UserPromptExpansion", {}, gate_py="import sys; sys.stderr.write('why'); sys.exit(10)\n")
        self.assertEqual(code, 2)
        self.assertIn("why", err)

    def test_hang_is_killed_and_follows_per_event_rule(self):
        hang = "import time; time.sleep(30)\n"
        start = time.time()
        self.assertEqual(self.sh("PreToolUse", {}, gate_py=hang, deadline="1")[0], 2)
        self.assertEqual(self.sh("SessionStart", {}, gate_py=hang, deadline="1"), (0, "", ""))
        self.assertEqual(self.sh("UserPromptExpansion", {}, gate_py=hang, deadline="1"), (0, "", ""))
        self.assertLess(time.time() - start, 15)

    def test_default_deadline_is_below_the_hook_timeout(self):
        self.assertRegex(GATE_SH.read_text(), r"YAB_GATE_DEADLINE:-([0-4])\b")

    def test_stdin_reaches_gate_py(self):
        echo = "import sys, json; sys.stdout.write(json.dumps({'got': len(sys.stdin.read())}))\n"
        code, out, _ = self.sh("SessionStart", "abcde", gate_py=echo)
        self.assertEqual((code, json.loads(out)), (0, {"got": 5}))

    def test_exit_codes_other_than_0_and_2_are_failures(self):
        self.assertEqual(self.sh("PreToolUse", {}, gate_py="import sys; sys.exit(1)\n")[0], 2)
        self.assertEqual(self.sh("PreToolUse", {}, gate_py="import sys; sys.exit(137)\n")[0], 2)

    def test_invalid_output_is_a_failure(self):
        junk = "print('hello')\n"
        self.assertEqual(self.sh("PreToolUse", {}, gate_py=junk)[0], 2)
        self.assertEqual(self.sh("SessionStart", {}, gate_py=junk), (0, "", ""))

    def test_missing_interpreter(self):
        missing = "/nonexistent/python-xyz"
        self.assertEqual(self.sh("PreToolUse", pre(self.root, "Read", {}), python=missing)[0], 2)
        self.assertEqual(self.sh("SessionStart", {}, python=missing), (0, "", ""))
        self.assertEqual(self.sh("UserPromptExpansion", {}, python=missing), (0, "", ""))

    def test_malformed_stdin_through_wrapper(self):
        self.project_dir(self.root)
        code, out, _ = self.sh("PreToolUse", "garbage")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(self.sh("SessionStart", "garbage"), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
