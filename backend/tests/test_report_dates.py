from datetime import date

import pytest

from app.modules.reports.dates import (
    END_DATE_REQUIRED,
    START_AFTER_END,
    START_DATE_REQUIRED,
    ReportPeriod,
    chart_days,
    period_bounds,
    resolve_report_bounds,
)


TODAY = date(2026, 8, 21)


def test_today_last_7_and_last_30_bounds():
    assert period_bounds(ReportPeriod.TODAY, TODAY) == (TODAY, TODAY)
    assert period_bounds(ReportPeriod.LAST_7_DAYS, TODAY) == (date(2026, 8, 15), TODAY)
    assert period_bounds(ReportPeriod.LAST_30_DAYS, TODAY) == (date(2026, 7, 23), TODAY)


def test_custom_bounds_are_inclusive():
    start = date(2026, 8, 1)
    end = date(2026, 8, 10)
    assert resolve_report_bounds(ReportPeriod.CUSTOM, start, end, today=TODAY) == (start, end)
    assert resolve_report_bounds(ReportPeriod.CUSTOM, end, end, today=TODAY) == (end, end)


def test_custom_bounds_validate_required_and_order():
    with pytest.raises(ValueError, match=START_DATE_REQUIRED):
        resolve_report_bounds(ReportPeriod.CUSTOM, None, date(2026, 8, 10), today=TODAY)
    with pytest.raises(ValueError, match=END_DATE_REQUIRED):
        resolve_report_bounds(ReportPeriod.CUSTOM, date(2026, 8, 1), None, today=TODAY)
    with pytest.raises(ValueError, match=START_AFTER_END):
        resolve_report_bounds(
            ReportPeriod.CUSTOM,
            date(2026, 8, 10),
            date(2026, 8, 1),
            today=TODAY,
        )


def test_predefined_chart_days_unchanged():
    assert chart_days(ReportPeriod.TODAY, TODAY) == [TODAY]
    week = chart_days(ReportPeriod.LAST_7_DAYS, TODAY)
    month = chart_days(ReportPeriod.LAST_30_DAYS, TODAY)
    assert len(week) == 7
    assert week[-1] == TODAY
    assert week[0] == date(2026, 8, 15)
    assert month == week


def test_custom_chart_days_include_end_date():
    days = chart_days(
        ReportPeriod.CUSTOM,
        TODAY,
        start=date(2026, 8, 8),
        end=date(2026, 8, 10),
    )
    assert days == [date(2026, 8, 8), date(2026, 8, 9), date(2026, 8, 10)]
