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
    provider_roles: dict     # role → provider name, e.g. {"pm": "linear", "vcs": "github"}
    provider_settings: dict  # provider name → settings dict, e.g. {"linear": {"project_id": "..."}}
    lmstudio_base: str
    model_tiers_path: str


_RESERVED_TOML_SECTIONS = {"providers", "llm", "core"}


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
    roles = data.get("providers", {})
    # Any top-level table not in reserved sections is provider settings
    settings = {k: v for k, v in data.items() if k not in _RESERVED_TOML_SECTIONS and isinstance(v, dict)}
    return Config(
        provider_roles=roles,
        provider_settings=settings,
        lmstudio_base=(
            os.environ.get("LMSTUDIO_BASE")
            or data.get("llm", {}).get("lmstudio_base", "http://localhost:1234/v1")
        ),
        model_tiers_path=data.get("core", {}).get("model_tiers_path", "docs/MODEL_TIERS.md"),
    )
