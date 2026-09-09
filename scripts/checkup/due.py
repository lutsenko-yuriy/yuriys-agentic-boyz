#!/usr/bin/env python3
"""due.py — Due-status detector for the two-tier periodic code-quality checkup.

Reads the cadence table in docs/knowledge/checkups/LEDGER.md and reports
which tier(s) — light, heavy — are due for review this period, per ADR-0001.
The report itself is advisory (never blocks CI or commits) and always exits
0; only setup errors (missing AGENTS.md, bad --format) exit non-zero.
Invoked by the /checkup skill and at session start.

Usage:
    python3 scripts/checkup/due.py [--root <path>] [--format table|session]

    --root    Project root directory (default: auto-detected from script location)
    --format  Output format: "table" (human-readable, default) or "session"
              (one-line-per-due-tier recommendation for session start)
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

LEDGER_REL_PATH = Path('docs/knowledge/checkups/LEDGER.md')

_CADENCE_SECTION_RE = re.compile(r'^## Cadence & due status\s*$', re.MULTILINE)
_NEXT_SECTION_RE = re.compile(r'^## ', re.MULTILINE)
_CADENCE_ROW_RE = re.compile(
    r'^\|\s*(Light|Heavy)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$',
    re.MULTILINE,
)

_HEAVY_ANCHOR_MONTHS = (1, 4, 7, 10)
_HEAVY_ANCHOR_DAY = 14

_CHECKUP_COMMAND = {'Light': '/checkup light', 'Heavy': '/checkup heavy'}


# ---------------------------------------------------------------------------
# Period math
# ---------------------------------------------------------------------------

def current_light_period(today: date) -> str:
    """Return the current calendar-month period label, e.g. '2026-07'."""
    return f'{today.year:04d}-{today.month:02d}'


def current_heavy_period(today: date) -> str:
    """Return the current quarter-anchor period label, e.g. '2026-Q3'.

    The period opened by an anchor (the 14th of Jan/Apr/Jul/Oct) stays
    current until the next anchor is reached — so on, say, Jan 5th, the
    current period is still the previous year's Q4 (opened Oct 14), not Q1.
    """
    candidates = [
        date(year, month, _HEAVY_ANCHOR_DAY)
        for year in (today.year - 1, today.year)
        for month in _HEAVY_ANCHOR_MONTHS
    ]
    anchor = max(d for d in candidates if d <= today)
    quarter = (anchor.month - 1) // 3 + 1
    return f'{anchor.year:04d}-Q{quarter}'


# ---------------------------------------------------------------------------
# Ledger parsing
# ---------------------------------------------------------------------------

def parse_ledger(text: str) -> dict[str, str]:
    """Return {'Light': period_covered, 'Heavy': period_covered} from the cadence table."""
    section_match = _CADENCE_SECTION_RE.search(text)
    section_start = section_match.end() if section_match else 0

    next_section_match = _NEXT_SECTION_RE.search(text, section_start)
    section_end = next_section_match.start() if next_section_match else len(text)

    search_text = text[section_start:section_end]

    periods: dict[str, str] = {}
    for match in _CADENCE_ROW_RE.finditer(search_text):
        tier, _cadence, _last_run, period_covered, _next_due = match.groups()
        periods[tier] = period_covered
    return periods


def due_status(periods: dict[str, str], today: date) -> dict[str, bool]:
    """Return {'Light': is_due, 'Heavy': is_due} given each tier's last covered period."""
    current = {
        'Light': current_light_period(today),
        'Heavy': current_heavy_period(today),
    }
    return {tier: periods.get(tier, '—') != current_period for tier, current_period in current.items()}


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_table(status: dict[str, bool]) -> str:
    lines = ['Checkup due status', '=' * 30]
    for tier in ('Light', 'Heavy'):
        state = 'DUE' if status.get(tier) else 'ok'
        lines.append(f'[{state}] {tier}')
    return '\n'.join(lines)


def format_session(status: dict[str, bool]) -> str:
    due_tiers = [tier for tier in ('Light', 'Heavy') if status.get(tier)]
    if not due_tiers:
        return ''
    recommendations = ', '.join(f'{tier} ({_CHECKUP_COMMAND[tier]})' for tier in due_tiers)
    return f'Checkup due: {recommendations} — consider running before picking up a new ticket.'


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(root: Path, today: date, fmt: str) -> None:
    ledger_path = root / LEDGER_REL_PATH
    text = ledger_path.read_text(encoding='utf-8') if ledger_path.exists() else ''
    periods = parse_ledger(text)
    status = due_status(periods, today)

    if fmt == 'session':
        message = format_session(status)
        if message:
            print(message)
    else:
        print(format_table(status))


def main() -> None:
    parser = argparse.ArgumentParser(description='Due-status detector for the periodic code-quality checkup')
    parser.add_argument('--root', default=None, help='Project root directory')
    parser.add_argument('--format', choices=('table', 'session'), default='table', help='Output format')
    args = parser.parse_args()

    if args.root:
        root = Path(args.root).resolve()
    else:
        root = Path(__file__).resolve().parent.parent.parent

    if not (root / 'AGENTS.md').exists():
        print(f'Error: {root} does not look like a project root (no AGENTS.md)',
              file=sys.stderr)
        sys.exit(1)

    run(root, date.today(), args.format)


if __name__ == '__main__':
    main()
