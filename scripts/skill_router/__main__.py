import sys
from pathlib import Path

# Allow invocation as `python3 scripts/skill_router` by ensuring the parent
# directory (scripts/) is on sys.path so absolute imports of the `skill_router`
# package work even when __main__.py is the entry point.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from skill_router.app import run
else:
    from .app import run

if __name__ == "__main__":
    sys.exit(run(sys.argv))
