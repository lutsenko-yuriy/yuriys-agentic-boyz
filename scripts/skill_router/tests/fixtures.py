from ..agentic.constants import MAX_TOOL_TURNS

_FM_PLAIN = ("RAPID", "MECHANICAL", False, None, [], MAX_TOOL_TURNS, "body")
_FM_SESSION_TOOLS = ("RAPID", "MECHANICAL", True, None, [], MAX_TOOL_TURNS, "body")
_FM_NO_EFFORT = (None, None, False, None, [], MAX_TOOL_TURNS, "body")
_FM_FOCUSED = ("FOCUSED", "ARCHITECTURAL", False, None, [], MAX_TOOL_TURNS, "body")
_FM_WITH_CONTEXT = ("RAPID", "MECHANICAL", False, "linear", [], MAX_TOOL_TURNS, "body")
_FM_WITH_TOOLS_LINEAR = ("RAPID", "MECHANICAL", False, None, ["linear"], MAX_TOOL_TURNS, "body")
_FM_WITH_TOOLS_GITHUB = ("RAPID", "MECHANICAL", False, None, ["github", "files"], MAX_TOOL_TURNS, "body")
