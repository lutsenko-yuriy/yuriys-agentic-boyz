"""Read-only Bash allowlist for the onboarding gate (HAB-278 WU3).

Pure function, stdlib only, Python 3.9 compatible: `is_allowed(command) -> (allowed, reason)`.
Fails closed: any parse error, unknown command, or unrecognised flag denies.

Deliberately over-strict: `$`, backticks, newlines and control characters are denied even inside quotes, and a
quoted operator-only token (e.g. `'|'`, `';'`) is indistinguishable from the operator after tokenising, so it is
treated as one (a quoted `'|'` splits the pipeline and usually fails on the empty or unknown segment). Braces are
denied for the same reason (bash brace expansion), which also rejects quoted jq object literals.

Flag checks follow getopt: a short cluster (`-ro`) is denied if any letter is denied, even one that is really another
flag's value, and a long option is denied if it is an abbreviation (`--out`) of a denied one. `--` is not trusted as
end-of-options: a value flag can swallow it (`sort -T -- -o out`), so arguments after it are checked too.

Known residuals (repo config, not command line): `diff.external`, textconv filters and `core.fsmonitor` in the target
repo's config can run programs on `git diff`/`log`/`status`. Unquoted globs still expand, so a file named like a flag
could inject one; nothing can create such a file while gated.
"""

import re
import shlex
from typing import List, Tuple

Result = Tuple[bool, str]

OK = (True, "ok")
OPERATOR_CHARS = frozenset("();<>|&")
FORBIDDEN_CHARS = ("$", "`", "{", "}", "\n", "\r", "\0")
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
PYTHON_RE = re.compile(r"^python3(\.\d+)?$")
ONBOARD_SCRIPTS = ("scripts/onboard/onboard.py", "./scripts/onboard/onboard.py")
ONBOARD_SUBCOMMANDS = frozenset({"probe", "check", "apply", "mark"})

INSPECTION_COMMANDS = (
    "ls pwd cat head tail wc file stat tree du diff cmp grep egrep rg cut tr jq basename dirname realpath which "
    "type date uname find sort uniq"
).split()

# Write/exec-capable flags per command, as (short letters, long names). From each man page: sort -o writes and
# --compress-program execs; rg --pre/--hostname-bin run programs; date -s sets the clock; tree -o writes and -R
# writes 00Tree.html per directory; file -C writes magic.mgc.
FIND_DENIED = frozenset("-exec -execdir -ok -okdir -delete -fprint -fprint0 -fprintf -fls".split())
UNIQ_VALUE_FLAGS = frozenset({"-f", "-s", "-w"})
FLAG_RULES = {
    "sort": (frozenset("o"), ("--output", "--compress-program")),
    "rg": (frozenset(), ("--pre", "--hostname-bin")),
    "date": (frozenset("s"), ("--set",)),
    "tree": (frozenset("oR"), ()),
    "file": (frozenset("C"), ("--compile",)),
}

GIT_READ_SUBCOMMANDS = frozenset(
    "status log show diff rev-parse ls-files ls-tree describe blame shortlog".split()
)
# Global options allowed before the subcommand. `-c` (config injection -> code exec), --exec-path, --git-dir and
# --work-tree (redirect git at attacker-chosen state) are not in this set, so they deny.
GIT_GLOBAL_FLAGS = frozenset({"--no-pager", "-P", "--no-optional-locks"})
# Anywhere after the subcommand: file writes and configured-program execution. Long options may be abbreviated.
GIT_DENIED_LONG = ("--output", "--ext-diff", "--textconv")
GIT_BRANCH_FLAGS = frozenset("--list -l -a --all -r --remotes -v -vv --show-current".split())
GIT_CONFIG_FLAGS = frozenset("--get --get-all --list -l --local --global --system --show-origin --null -z".split())
GIT_TAG_FLAGS = frozenset({"-l", "--list", "-n"})

GH_COMMANDS = frozenset({("auth", "status"), ("repo", "view"), ("issue", "list"), ("issue", "view")})
# --web opens a browser (not read-only/non-interactive); --show-token prints the credential.
GH_DENIED = (frozenset("wt"), ("--web", "--show-token"))


def is_allowed(command: str) -> Result:
    """Return (allowed, reason) for a Bash command line; every `|` segment must pass independently."""
    if not command or not command.strip():
        return False, "empty command"
    if any(ch in command for ch in FORBIDDEN_CHARS):
        return False, "substitution, expansion or newline not allowed"
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ""
        tokens = list(lex)
    except ValueError as exc:
        return False, "parse error: %s" % exc
    segments = []  # type: List[List[str]]
    current = []  # type: List[str]
    for tok in tokens:
        if tok and all(ch in OPERATOR_CHARS for ch in tok):
            if tok != "|":
                return False, "operator %r not allowed" % tok
            segments.append(current)
            current = []
        else:
            current.append(tok)
    segments.append(current)
    for seg in segments:
        ok, reason = _check_segment(seg)
        if not ok:
            return False, reason
    return OK


def _check_segment(seg: List[str]) -> Result:
    if not seg:
        return False, "empty pipeline segment"
    name, args = seg[0], seg[1:]
    if ENV_ASSIGN_RE.match(name):
        return False, "environment assignment prefix not allowed"
    base = name.rsplit("/", 1)[-1]
    if PYTHON_RE.match(base) and (base == name or name.startswith("/")):
        return _check_onboard(args)
    if "/" in name:
        return False, "path-qualified command %r not allowed" % name
    if name == "git":
        return _check_git(args)
    if name == "gh":
        return _check_gh(args)
    if name in INSPECTION_COMMANDS:
        return _check_inspection(name, args)
    return False, "command %r not allowlisted" % name


def _long_name(arg: str) -> str:
    return arg.split("=", 1)[0]


def _check_inspection(name: str, args: List[str]) -> Result:
    if name == "find":
        bad = next((a for a in args if a in FIND_DENIED), "")
    elif name == "uniq":
        bad = _uniq_extra_arg(args)
    elif name in FLAG_RULES:
        bad = _denied_flag(args, *FLAG_RULES[name])
    else:
        bad = ""
    if bad:
        return False, "%s: denied flag/argument %r" % (name, bad)
    return OK


def _uniq_extra_arg(args: List[str]) -> str:
    """Return the first arg after uniq's input operand: BSD uniq reads the next arg as the output file, `-x` included."""
    i, after_dashdash = 0, False
    while i < len(args):
        arg = args[i]
        if arg == "--" and not after_dashdash:
            after_dashdash = True
        elif after_dashdash or arg == "-" or not arg.startswith("-"):
            return repr(args[i + 1]) if i + 1 < len(args) else ""
        elif arg in UNIQ_VALUE_FLAGS:
            i += 1
        i += 1
    return ""


def _denied_flag(args: List[str], short: frozenset, long_names: Tuple[str, ...]) -> str:
    """Return the first arg that is, contains (short cluster) or abbreviates (long) a denied flag."""
    for arg in args:
        if arg == "--":
            continue
        if arg.startswith("--"):
            name = _long_name(arg)
            if any(name.startswith(full) or (len(name) >= 3 and full.startswith(name)) for full in long_names):
                return arg
        elif arg.startswith("-") and short & set(arg[1:]):
            return arg
    return ""


def _check_git(args: List[str]) -> Result:
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-C" and i + 1 < len(args):
            i += 2
        elif args[i] in GIT_GLOBAL_FLAGS:
            i += 1
        else:
            return False, "git: global option %r not allowed" % args[i]
    if i >= len(args):
        return False, "git: no subcommand"
    sub, rest = args[i], args[i + 1:]
    bad = _denied_flag(rest, frozenset(), GIT_DENIED_LONG)
    if bad:
        return False, "git: %r writes files or runs configured programs" % bad
    if sub in GIT_READ_SUBCOMMANDS:
        return OK
    opts = [a for a in rest if a.startswith("-")]
    pos = [a for a in rest if not a.startswith("-")]
    if sub == "worktree":
        return OK if rest[:1] == ["list"] and all(a in ("list", "--porcelain", "-v") for a in rest) else (
            False, "git worktree: only 'list' allowed")
    if sub == "branch":
        if any(a not in GIT_BRANCH_FLAGS for a in opts):
            return False, "git branch: only listing flags allowed"
        if pos and not ({"--list", "-l"} & set(opts)):
            return False, "git branch: positional argument requires --list"
        return OK
    if sub == "remote":
        if rest in ([], ["-v"]) or (len(rest) == 2 and rest[0] in ("get-url", "show") and not rest[1].startswith("-")):
            return OK
        return False, "git remote: only -v, get-url, show allowed"
    if sub == "config":
        if any(a not in GIT_CONFIG_FLAGS for a in opts):
            return False, "git config: only read flags allowed"
        if pos and not ({"--get", "--get-all"} & set(opts)):
            return False, "git config: positional argument requires --get/--get-all"
        return OK
    if sub == "tag":
        if any(a not in GIT_TAG_FLAGS for a in opts) or not ({"-l", "--list"} & set(opts)):
            return False, "git tag: --list required, no other flags"
        return OK
    return False, "git: subcommand %r not allowed" % sub


def _check_gh(args: List[str]) -> Result:
    if len(args) < 2 or (args[0], args[1]) not in GH_COMMANDS:
        return False, "gh: only auth status, repo view, issue list/view allowed"
    bad = _denied_flag(args[2:], *GH_DENIED)
    if bad:
        return False, "gh: flag %r not allowed" % bad
    return OK


def _check_onboard(args: List[str]) -> Result:
    if len(args) != 2 or args[0] not in ONBOARD_SCRIPTS or args[1] not in ONBOARD_SUBCOMMANDS:
        return False, "python: only `scripts/onboard/onboard.py <probe|check|apply|mark>` with no other arguments"
    return OK
