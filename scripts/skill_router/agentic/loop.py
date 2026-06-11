from __future__ import annotations

import json
import sys
import urllib.request

from ..llm.constants import LMSTUDIO_BASE
from ..llm.lm_studio import _auth_headers
from .constants import MAX_TOOL_TURNS
from .registry import ProviderRegistry


def chat_completion_with_tools(
    model_name: str,
    prompt: str,
    registry: ProviderRegistry,
    *,
    max_turns: int = MAX_TOOL_TURNS,
) -> bool:
    messages = [{"role": "user", "content": prompt}]
    tools = registry.tool_schemas()
    for turn in range(max_turns):
        payload = json.dumps({
            "model": model_name,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            f"{LMSTUDIO_BASE}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", **_auth_headers()},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.load(resp)
        except Exception as e:
            print(f"\n[skill_router] Tool loop error on turn {turn + 1}: {e}", file=sys.stderr)
            return False
        if not data.get("choices"):
            print("[skill_router] Empty response from model", file=sys.stderr)
            return False
        choice = data["choices"][0]
        msg = choice["message"]
        finish_reason = choice.get("finish_reason", "stop")
        tool_calls = msg.get("tool_calls") or []
        if tool_calls and finish_reason in ("tool_calls", None, ""):
            messages.append(msg)
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except (json.JSONDecodeError, TypeError):
                    fn_args = {}
                print(f"[tool:{turn + 1}] {fn_name}({json.dumps(fn_args)[:120]})", file=sys.stderr)
                result = registry.dispatch(fn_name, fn_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result if isinstance(result, str) else json.dumps(result),
                })
        else:
            content = msg.get("content") or ""
            print(content, flush=True)
            print()
            return True
    print(f"[skill_router] Tool loop hit max turns ({max_turns})", file=sys.stderr)
    return False
