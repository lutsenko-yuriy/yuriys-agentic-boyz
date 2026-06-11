from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ImportError:
    tomllib = None


@dataclass(frozen=True)
class Config:
    linear_api_key: str | None
    linear_project_id: str | None
    lmstudio_base: str
    model_tiers_path: str


def _load_toml(path: Path) -> dict:
    if tomllib is None or not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"[skill_router] Warning: could not read {path}: {e}", file=sys.stderr)
        return {}


def load_config(toml_path: str = "skill_router.toml") -> Config:
    data = _load_toml(Path(toml_path))
    return Config(
        linear_api_key=os.environ.get("LINEAR_API_KEY"),
        linear_project_id=(
            os.environ.get("LINEAR_PROJECT_ID")
            or data.get("linear", {}).get("project_id")
        ),
        lmstudio_base=(
            os.environ.get("LMSTUDIO_BASE")
            or data.get("llm", {}).get("lmstudio_base", "http://localhost:1234/v1")
        ),
        model_tiers_path=data.get("core", {}).get("model_tiers_path", "docs/MODEL_TIERS.md"),
    )
