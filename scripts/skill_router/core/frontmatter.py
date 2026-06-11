import re
from pathlib import Path


def read_frontmatter(skill_path: str):
    """Return (effort, reasoning, needs_session_tools, context, tools, max_turns, body)."""
    from .constants import DEFAULT_MAX_TURNS as MAX_TOOL_TURNS
    text = Path(skill_path).read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None, None, False, None, [], MAX_TOOL_TURNS, text
    fm = m.group(1)
    effort = re.search(r"^effort:\s*(\S+)", fm, re.MULTILINE)
    reasoning = re.search(r"^reasoning:\s*(\S+)", fm, re.MULTILINE)
    needs_session_tools = bool(re.search(r"^needs_session_tools:\s*true", fm, re.MULTILINE))
    context_match = re.search(r"^context:\s*(\S+)", fm, re.MULTILINE)
    tools_match = re.search(r"^tools:\s*(.+)$", fm, re.MULTILINE)
    tools = [t.strip() for t in tools_match.group(1).split(",")] if tools_match else []
    max_turns_match = re.search(r"^max_turns:\s*(\d+)", fm, re.MULTILINE)
    max_turns = int(max_turns_match.group(1)) if max_turns_match else MAX_TOOL_TURNS
    return (
        effort.group(1) if effort else None,
        reasoning.group(1) if reasoning else None,
        needs_session_tools,
        context_match.group(1) if context_match else None,
        tools,
        max_turns,
        text[m.end():],
    )
