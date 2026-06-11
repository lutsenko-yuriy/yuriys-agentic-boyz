import json
import os
import urllib.request

from .constants import LMSTUDIO_BASE
from ..core.model_resolver import normalize_model_name


def _auth_headers() -> dict:
    token = os.environ.get("LM_API_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def model_loaded(model_name: str) -> bool:
    try:
        req = urllib.request.Request(f"{LMSTUDIO_BASE}/models", headers=_auth_headers())
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.load(resp)
        loaded_ids = [m["id"] for m in data.get("data", [])]
        needle = normalize_model_name(model_name)
        return any(
            needle in normalize_model_name(mid) or normalize_model_name(mid) in needle
            for mid in loaded_ids
        )
    except Exception:
        return False


def stream_completion(model_name: str, prompt: str) -> bool:
    payload = json.dumps({
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }).encode()
    req = urllib.request.Request(
        f"{LMSTUDIO_BASE}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", **_auth_headers()},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw_line in resp:
                line = raw_line.decode().strip()
                if not line.startswith("data: "):
                    continue
                payload_str = line[6:]
                if payload_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload_str)
                    content = chunk["choices"][0]["delta"].get("content", "")
                    if content:
                        print(content, end="", flush=True)
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    pass
        print()
        return True
    except Exception as e:
        import sys
        print(f"\n[skill_router] Streaming error: {e}", file=sys.stderr)
        return False
