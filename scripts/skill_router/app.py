from __future__ import annotations

import sys
from pathlib import Path

from .config import load_config
from .core.frontmatter import read_frontmatter
from .core.model_resolver import lookup_lmstudio_model, normalize_model_name
from .llm.lm_studio import model_loaded, stream_completion
from .agentic.loop import chat_completion_with_tools
from .agentic.registry import ProviderRegistry
from .providers.linear.provider import LinearProvider
from .providers.github.provider import GithubProvider
from .providers.files.provider import FilesProvider


_PROVIDER_FACTORIES = {
    "linear": lambda cfg: LinearProvider(cfg.linear_api_key, cfg.linear_project_id),
    "github": lambda cfg: GithubProvider(),
    "files": lambda cfg: FilesProvider(project_root="."),
}


def run(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: skill_router <skill_path> [--args <extra>]", file=sys.stderr)
        return 2

    skill_path = argv[1]
    extra_args = ""
    if "--args" in argv:
        idx = argv.index("--args")
        extra_args = " ".join(argv[idx + 1:]).strip()

    if not Path(skill_path).exists():
        print(f"[skill_router] Skill file not found: {skill_path}", file=sys.stderr)
        return 2

    effort, reasoning, needs_session_tools, context, tool_groups, max_turns, body = read_frontmatter(skill_path)
    if not effort or not reasoning:
        print(f"[skill_router] Could not parse frontmatter in {skill_path}", file=sys.stderr)
        return 2

    if needs_session_tools:
        print(
            f"[skill_router] {skill_path} requires session tools (MCP/Bash/Edit) — "
            "must run inside Claude Code, not via LM Studio",
            file=sys.stderr,
        )
        return 2

    cfg = load_config()

    if context:
        ctx_factory = _PROVIDER_FACTORIES.get(context)
        if not ctx_factory:
            print(f"[skill_router] Unknown context provider '{context}'", file=sys.stderr)
            return 2
        ctx_provider = ctx_factory(cfg)
        err = ctx_provider.validate()
        if err:
            print(f"[skill_router] {err}", file=sys.stderr)
            return 2
        try:
            body = f"{ctx_provider.format_context(ctx_provider.fetch_context())}\n\n{body}"
        except Exception as e:
            print(f"[skill_router] Failed to fetch context: {e}", file=sys.stderr)
            return 1

    providers = []
    for group in tool_groups:
        factory = _PROVIDER_FACTORIES.get(group)
        if factory is None:
            print(f"[skill_router] Unknown tool group '{group}' — skipping", file=sys.stderr)
            continue
        provider = factory(cfg)
        err = provider.validate()
        if err:
            print(f"[skill_router] {err}", file=sys.stderr)
            return 2
        providers.append(provider)

    model_name = lookup_lmstudio_model(effort, reasoning, cfg.model_tiers_path)
    if not model_name:
        print(f"[skill_router] No lm-studio mapping for {effort}+{reasoning}", file=sys.stderr)
        return 2

    if not model_loaded(model_name):
        print(f"[skill_router] LM Studio unavailable or model not loaded: {model_name}", file=sys.stderr)
        return 1

    api_model_name = normalize_model_name(model_name)
    prompt = f"{body}\n\n---\n\n{extra_args}" if extra_args else body

    if providers:
        registry = ProviderRegistry(providers)
        success = chat_completion_with_tools(api_model_name, prompt, registry, max_turns=max_turns)
    else:
        success = stream_completion(api_model_name, prompt)

    return 0 if success else 1
