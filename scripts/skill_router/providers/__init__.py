from .linear.provider import LinearProvider
from .github.provider import GithubProvider
from .files.provider import FilesProvider

# Register provider name → class here.
# To add a new tool: implement scripts/skill_router/providers/<name>/provider.py
# and add an entry below. No other files need to change.
PROVIDER_REGISTRY: dict[str, type] = {
    "linear": LinearProvider,
    "github": GithubProvider,
    "files": FilesProvider,
}
