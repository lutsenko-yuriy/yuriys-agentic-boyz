from __future__ import annotations

import unittest
from datetime import date

from checkup.due import current_heavy_period, current_light_period, due_status, parse_ledger

_LEDGER_TEMPLATE = """# Checkup ledger

## Cadence & due status

| Tier | Cadence | Last run | Period covered | Next due |
|---|---|---|---|---|
| Light | 1st of every calendar month | {light_last_run} | {light_period} | — |
| Heavy | 14th of Jan/Apr/Jul/Oct | {heavy_last_run} | {heavy_period} | — |

## Open findings

| ID | Opened | Tier | Dimension | Debt quadrant | Summary | Deadline | Write-up |
|---|---|---|---|---|---|---|---|
| _none yet_ | | | | | | | |
"""


def _ledger(light_period: str = '—', heavy_period: str = '—',
            light_last_run: str = 'never', heavy_last_run: str = 'never') -> str:
    return _LEDGER_TEMPLATE.format(
        light_period=light_period,
        heavy_period=heavy_period,
        light_last_run=light_last_run,
        heavy_last_run=heavy_last_run,
    )


class TestCurrentLightPeriod(unittest.TestCase):

    def test_formats_as_year_month(self):
        self.assertEqual(current_light_period(date(2026, 7, 15)), '2026-07')

    def test_pads_single_digit_month(self):
        self.assertEqual(current_light_period(date(2026, 1, 5)), '2026-01')


class TestCurrentHeavyPeriod(unittest.TestCase):

    def test_on_anchor_day_starts_new_quarter(self):
        self.assertEqual(current_heavy_period(date(2026, 1, 14)), '2026-Q1')

    def test_before_anchor_day_still_previous_quarter(self):
        # Jan 5 is before the Jan-14 anchor, so the current period is still
        # the one opened by the most recently passed anchor: Oct-14 of the
        # previous year.
        self.assertEqual(current_heavy_period(date(2026, 1, 5)), '2025-Q4')

    def test_non_anchor_month_uses_most_recent_passed_anchor(self):
        self.assertEqual(current_heavy_period(date(2026, 5, 20)), '2026-Q2')

    def test_year_rollover_after_october_anchor(self):
        self.assertEqual(current_heavy_period(date(2026, 12, 20)), '2026-Q4')

    def test_year_rollover_before_january_anchor_next_year(self):
        self.assertEqual(current_heavy_period(date(2027, 1, 10)), '2026-Q4')


class TestParseLedger(unittest.TestCase):

    def test_extracts_period_covered_per_tier(self):
        text = _ledger(light_period='2026-07', heavy_period='2026-Q3')
        periods = parse_ledger(text)
        self.assertEqual(periods['Light'], '2026-07')
        self.assertEqual(periods['Heavy'], '2026-Q3')

    def test_never_run_period_is_em_dash(self):
        periods = parse_ledger(_ledger())
        self.assertEqual(periods['Light'], '—')
        self.assertEqual(periods['Heavy'], '—')

    def test_open_findings_table_does_not_pollute_cadence_rows(self):
        text = _ledger(light_period='2026-07', heavy_period='2026-Q3') + (
            '\n| Light bulb | some finding | Heavy | dimension | prudent-inadvertent |'
            ' summary | 2026-08-01 | CHK-2026-07-01-light.md |\n'
        )
        periods = parse_ledger(text)
        self.assertEqual(periods['Light'], '2026-07')
        self.assertEqual(periods['Heavy'], '2026-Q3')

    def test_scan_stops_at_next_heading_even_with_matching_row_shape(self):
        # A later section with a 5-column row whose first cell happens to be
        # "Light"/"Heavy" must not override the real cadence-table values.
        text = _ledger(light_period='2026-07', heavy_period='2026-Q3') + (
            '\n## Some later section\n\n'
            '| Light | a | b | 9999-99 | z |\n'
            '| Heavy | a | b | 9999-99 | z |\n'
        )
        periods = parse_ledger(text)
        self.assertEqual(periods['Light'], '2026-07')
        self.assertEqual(periods['Heavy'], '2026-Q3')


class TestDueStatus(unittest.TestCase):

    def test_never_run_is_due(self):
        periods = parse_ledger(_ledger())
        status = due_status(periods, date(2026, 7, 15))
        self.assertTrue(status['Light'])
        self.assertTrue(status['Heavy'])

    def test_light_run_this_month_is_not_due(self):
        periods = parse_ledger(_ledger(light_period='2026-07'))
        status = due_status(periods, date(2026, 7, 15))
        self.assertFalse(status['Light'])

    def test_light_run_last_month_is_due(self):
        periods = parse_ledger(_ledger(light_period='2026-06'))
        status = due_status(periods, date(2026, 7, 1))
        self.assertTrue(status['Light'])

    def test_heavy_run_this_quarter_is_not_due(self):
        periods = parse_ledger(_ledger(heavy_period='2026-Q3'))
        status = due_status(periods, date(2026, 7, 15))
        self.assertFalse(status['Heavy'])

    def test_heavy_not_yet_run_before_anchor_day_is_due(self):
        # Jan 5: current heavy period is 2025-Q4 (still open until Jan 14).
        # If 2025-Q4 was never covered, it's due — carried over, not "new".
        periods = parse_ledger(_ledger(heavy_period='2025-Q3'))
        status = due_status(periods, date(2026, 1, 5))
        self.assertTrue(status['Heavy'])

    def test_heavy_mid_quarter_non_anchor_month_stays_not_due(self):
        periods = parse_ledger(_ledger(heavy_period='2026-Q2'))
        status = due_status(periods, date(2026, 5, 20))
        self.assertFalse(status['Heavy'])


if __name__ == '__main__':
    unittest.main()
