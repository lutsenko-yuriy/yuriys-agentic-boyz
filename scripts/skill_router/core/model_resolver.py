from __future__ import annotations

import re
import sys
from pathlib import Path


def normalize_model_name(name: str) -> str:
    return re.split(r"[\s(]", name.strip())[0].lower()


_normalize_model_name = normalize_model_name


def lookup_lmstudio_model(effort: str, reasoning: str, tiers_path: str = None) -> str | None:
    from .constants import MODEL_TIERS_PATH
    tiers_path = tiers_path or MODEL_TIERS_PATH
    try:
        tiers_text = Path(tiers_path).read_text()
    except FileNotFoundError:
        print(f"[skill_router] {tiers_path} not found", file=sys.stderr)
        return None

    section = re.search(r"## Active mapping\n(.*?)\n---", tiers_text, re.DOTALL)
    if not section:
        print(f"[skill_router] '## Active mapping' section not found in {tiers_path}", file=sys.stderr)
        return None

    for line in section.group(1).splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5:
            continue
        row_effort, row_reasoning, model, alias = parts[1], parts[2], parts[3], parts[4]
        if row_effort == effort and row_reasoning == reasoning:
            return model if alias.strip("`") == "lm-studio" else None

    return None
