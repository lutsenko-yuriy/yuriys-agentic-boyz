import unittest

from scripts.onboard import bash_policy

ONBOARD = "scripts/onboard/onboard.py"


class PolicyCase(unittest.TestCase):
    def allow(self, cmd):
        ok, reason = bash_policy.is_allowed(cmd)
        self.assertTrue(ok, "expected allow: %r (%s)" % (cmd, reason))

    def deny(self, cmd):
        ok, reason = bash_policy.is_allowed(cmd)
        self.assertFalse(ok, "expected deny: %r" % (cmd,))
        self.assertTrue(reason)


class ParseTests(PolicyCase):
    def test_deny_empty_string(self):
        self.deny("")
        self.deny("   ")

    def test_deny_unbalanced_quote(self):
        self.deny("grep 'abc f")

    def test_deny_command_substitution_dollar_paren(self):
        self.deny("ls $(whoami)")

    def test_deny_backticks(self):
        self.deny("ls `id`")

    def test_deny_dollar_expansion(self):
        self.deny("ls ${HOME}")
        self.deny("ls $HOME")

    def test_deny_newline(self):
        self.deny("ls\nrm x")

    def test_deny_semicolon(self):
        self.deny("ls; rm -rf /")

    def test_deny_and_and(self):
        self.deny("a && b")
        self.deny("ls && ls")

    def test_deny_or_or(self):
        self.deny("ls || ls")

    def test_deny_background_amp(self):
        self.deny("ls &")

    def test_deny_redirect_out(self):
        self.deny("cat x > y")
        self.deny("cat x >> y")

    def test_deny_redirect_in_and_heredoc(self):
        self.deny("cat < y")
        self.deny("cat << EOF")

    def test_deny_fd_dup(self):
        self.deny("ls 2>&1")

    def test_deny_pipe_amp(self):
        self.deny("ls |& cat")

    def test_deny_subshell_parens(self):
        self.deny("(ls)")

    def test_deny_env_assignment_prefix(self):
        self.deny("FOO=1 ls")

    def test_deny_empty_pipe_segment(self):
        self.deny("ls |")
        self.deny("| ls")
        self.deny("ls | | cat")

    def test_allow_quoted_arrow_argument(self):
        self.allow("grep '->' f")

    def test_allow_pipe_between_allowed_segments(self):
        self.allow("ls -la | grep foo | wc -l")

    def test_deny_pipe_when_any_segment_denied(self):
        self.deny("git log | sh")
        self.deny("cat f | xargs rm")
        self.deny("sh | ls")


class CommandNameTests(PolicyCase):
    def test_allow_inspection_allowlist(self):
        for name in bash_policy.INSPECTION_COMMANDS:
            self.allow(name + " x")

    def test_deny_path_qualified_command(self):
        self.deny("./ls")
        self.deny("/bin/ls")
        self.deny("/bin/rm x")

    def test_deny_not_allowlisted_commands(self):
        for name in "awk sed xargs echo tee env sh bash zsh eval exec sudo rm mv cp touch mkdir chmod npm".split():
            self.deny(name + " x")

    def test_deny_flutter_version(self):
        self.deny("flutter --version")

    def test_deny_gradlew_version(self):
        self.deny("./gradlew --version")

    def test_deny_pty_wrapper_script(self):
        self.deny("script -q /dev/null python3 %s mark --force" % ONBOARD)
        self.deny("script -q /dev/null ls")

    def test_deny_pty_wrapper_expect(self):
        self.deny("expect -c 'spawn ls'")

    def test_deny_pty_wrapper_unbuffer(self):
        self.deny("unbuffer python3 %s mark --force" % ONBOARD)


class FlagTests(PolicyCase):
    def test_deny_find_exec_family(self):
        for flag in "-exec -execdir -ok -okdir".split():
            self.deny("find . %s rm {} +" % flag)
        self.deny("find . -exec rm {} \\;")

    def test_deny_find_delete(self):
        self.deny("find . -delete")

    def test_deny_find_fprint_family(self):
        for flag in "-fprint -fprint0 -fprintf -fls".split():
            self.deny("find . %s out" % flag)

    def test_allow_find_plain(self):
        self.allow("find . -name '*.py' -type f")

    def test_deny_sort_output_flag(self):
        self.deny("sort -o out in")
        self.deny("sort -oout in")
        self.deny("sort --output=out in")
        self.deny("sort --output out in")

    def test_deny_sort_compress_program(self):
        self.deny("sort --compress-program=sh in")

    def test_allow_sort_plain(self):
        self.allow("sort -u f")

    def test_deny_uniq_two_paths(self):
        self.deny("uniq a b")

    def test_allow_uniq_one_path(self):
        self.allow("uniq -c a")
        self.allow("uniq")

    def test_deny_date_set(self):
        self.deny("date -s 2020-01-01")
        self.deny("date --set=2020-01-01")

    def test_allow_date_plain(self):
        self.allow("date +%Y")

    def test_deny_rg_pre(self):
        self.deny("rg --pre sh foo")
        self.deny("rg --pre=sh foo")

    def test_deny_rg_hostname_bin(self):
        self.deny("rg --hostname-bin=sh foo")

    def test_deny_tree_output(self):
        self.deny("tree -o out")

    def test_deny_file_compile(self):
        self.deny("file -C")
        self.deny("file --compile")


class GitTests(PolicyCase):
    def test_allow_git_read_subcommands(self):
        for sub in "status log show diff rev-parse ls-files ls-tree describe blame shortlog".split():
            self.allow("git " + sub)

    def test_allow_git_worktree_list(self):
        self.allow("git worktree list")

    def test_deny_git_worktree_add(self):
        self.deny("git worktree add x")

    def test_allow_git_dash_C(self):
        self.allow("git -C /some/dir status")

    def test_deny_git_dash_c_config_injection(self):
        self.deny("git -c core.pager=sh log")
        self.deny("git -ccore.pager=sh log")

    def test_deny_git_global_exec_path_and_git_dir(self):
        self.deny("git --exec-path=/x log")
        self.deny("git --git-dir=/x log")
        self.deny("git --work-tree=/x log")

    def test_deny_git_output_flag(self):
        self.deny("git diff --output=x")
        self.deny("git log --output x")
        self.deny("git diff --outp=x")

    def test_deny_git_ext_diff_and_textconv(self):
        self.deny("git diff --ext-diff")
        self.deny("git log -p --textconv")

    def test_allow_git_no_ext_diff_and_no_textconv(self):
        self.allow("git diff --no-ext-diff --no-textconv")

    def test_allow_git_diff_no_index(self):
        self.allow("git diff --no-index a b")

    def test_deny_git_write_subcommands(self):
        for sub in "commit push pull checkout reset rebase merge add rm stash clean fetch clone init".split():
            self.deny("git " + sub)

    def test_deny_git_unknown_alias(self):
        self.deny("git foo")

    def test_deny_git_no_subcommand(self):
        self.deny("git")
        self.deny("git -C /x")

    def test_allow_git_branch_list_forms(self):
        for args in ["--list", "-a", "-r", "-v", "-vv", "--show-current", "--list 'feature/*'"]:
            self.allow("git branch " + args)
        self.allow("git branch")

    def test_deny_git_branch_positional_without_list(self):
        self.deny("git branch newbranch")
        self.deny("git branch -D x")
        self.deny("git branch -m a b")

    def test_allow_git_remote_read_forms(self):
        self.allow("git remote")
        self.allow("git remote -v")
        self.allow("git remote get-url origin")
        self.allow("git remote show origin")

    def test_deny_git_remote_write_forms(self):
        self.deny("git remote add x y")
        self.deny("git remote remove x")
        self.deny("git remote set-url x y")

    def test_allow_git_config_read_forms(self):
        for args in ["--get user.name", "--get-all remote.origin.url", "--list", "-l"]:
            self.allow("git config " + args)

    def test_deny_git_config_write_forms(self):
        self.deny("git config user.name x")
        self.deny("git config --unset user.name")
        self.deny("git config --add a.b c")
        self.deny("git config -e")
        self.deny("git config core.pager sh")

    def test_allow_git_tag_list(self):
        self.allow("git tag -l")
        self.allow("git tag --list 'v*'")

    def test_deny_git_tag_without_list(self):
        self.deny("git tag v1")
        self.deny("git tag -d v1")
        self.deny("git tag")


class GhTests(PolicyCase):
    def test_allow_gh_read_commands(self):
        self.allow("gh auth status")
        self.allow("gh repo view")
        self.allow("gh issue list")
        self.allow("gh issue view 12")

    def test_deny_gh_write_commands(self):
        self.deny("gh issue create")
        self.deny("gh pr merge 1")
        self.deny("gh api -X POST /x")
        self.deny("gh repo delete")
        self.deny("gh auth login")

    def test_deny_gh_web_flag(self):
        self.deny("gh issue view 1 --web")
        self.deny("gh repo view -w")

    def test_deny_gh_show_token(self):
        self.deny("gh auth status --show-token")
        self.deny("gh auth status -t")


class OnboardTests(PolicyCase):
    def test_allow_onboard_subcommands(self):
        for sub in "probe check apply mark".split():
            self.allow("python3 %s %s" % (ONBOARD, sub))

    def test_allow_onboard_dot_slash_script(self):
        self.allow("python3 ./%s probe" % ONBOARD)

    def test_allow_onboard_python_versions_and_abs_path(self):
        self.allow("python3.12 %s check" % ONBOARD)
        self.allow("/opt/homebrew/bin/python3.12 %s check" % ONBOARD)
        self.allow("/usr/bin/python3 %s probe" % ONBOARD)

    def test_deny_onboard_mark_force(self):
        self.deny("python3 %s mark --force" % ONBOARD)
        self.deny("python3 %s mark --fo" % ONBOARD)
        self.deny("python3 %s mark -- --force" % ONBOARD)

    def test_deny_onboard_extra_args_or_global_flags(self):
        self.deny("python3 %s probe extra" % ONBOARD)
        self.deny("python3 %s --root /x mark" % ONBOARD)

    def test_deny_onboard_unknown_subcommand(self):
        self.deny("python3 %s bogus" % ONBOARD)
        self.deny("python3 %s" % ONBOARD)

    def test_deny_python_dash_c(self):
        self.deny("python3 -c 'print(1)'")

    def test_deny_python_other_flags_and_scripts(self):
        self.deny("python3 -m http.server")
        self.deny("python3 -I %s probe" % ONBOARD)
        self.deny("python3 other.py probe")
        self.deny("python3 ../%s probe" % ONBOARD)

    def test_deny_python_bad_binary_name(self):
        self.deny("/tmp/python3x %s probe" % ONBOARD)
        self.deny("/tmp/evil/python %s probe" % ONBOARD)
        self.deny("python %s probe" % ONBOARD)


if __name__ == "__main__":
    unittest.main()


class ExpansionAndClusterTests(PolicyCase):
    def test_deny_brace_expansion(self):
        self.deny("git log {--output=pwned,}")
        self.deny("find d {-delete,-print}")
        self.deny("sort {-o,out} in")
        self.deny("rg {--pre=sh,} x f")

    def test_deny_sort_clustered_output_flag(self):
        self.deny("sort -ro out in")
        self.deny("sort -mo out in")
        self.deny("sort -uo out in")

    def test_deny_sort_abbreviated_long_flags(self):
        self.deny("sort --out=out in")
        self.deny("sort --o out in")
        self.deny("sort --compress-prog=sh in")

    def test_deny_denied_flag_after_double_dash(self):
        # A value flag can swallow `--`, so flags after it still parse as flags.
        self.deny("sort -T -- -o out in")
        self.deny("file -m -- -C")
        self.deny("rg -e -- --pre=sh x f")
        self.deny("git blame -L -- --output=pw README.md")
        self.deny("tree -P -- -o out .")
        self.deny("gh auth status -h -- --show-token")

    def test_deny_uniq_stdin_dash_and_double_dash_output(self):
        self.deny("cat in | uniq - out")
        self.deny("uniq -- in out")

    def test_deny_uniq_arg_after_first_operand(self):
        self.deny("uniq in -out")
        self.deny("cat in | uniq - -out")
        self.deny("uniq in '' out")

    def test_allow_uniq_value_flags_before_operand(self):
        self.allow("uniq -c -f 1 -s 2 in")

    def test_allow_uniq_stdin_dash_alone(self):
        self.allow("cat in | uniq -c -")

    def test_deny_tree_clustered_output_and_html_rewrite(self):
        self.deny("tree -ao out .")
        self.deny("tree -R -H . -L 2")

    def test_deny_file_clustered_and_abbreviated_compile(self):
        self.deny("file -zC -m in")
        self.deny("file --comp -m in")

    def test_deny_date_clustered_and_abbreviated_set(self):
        self.deny("date -us 1200")
        self.deny("date --se=1200")

    def test_deny_rg_abbreviated_pre(self):
        self.deny("rg --pr=sh x f")

    def test_deny_gh_clustered_web_and_token(self):
        self.deny("gh auth status -th github.com")
        self.deny("gh repo view -wb main")
        self.deny("gh repo view --we")
