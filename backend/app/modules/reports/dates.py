"""Date-range helpers for M9 reports.

Uses the same UTC calendar-day semantics as M7 completed-bill filters.
Do not introduce a separate IST / business-day model.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from enum import StrEnum


class ReportPeriod(StrEnum):
    TODAY = 'today'
    LAST_7_DAYS = '7d'
    LAST_30_DAYS = '30d'
    CUSTOM = 'custom'


START_DATE_REQUIRED = 'Start date is required.'
END_DATE_REQUIRED = 'End date is required.'
START_AFTER_END = 'Start date cannot be after end date.'


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def resolve_sales_date(selected: date | None = None, *, today: date | None = None) -> date:
    """Single UTC calendar day for employee daily sales.

    Omitted date defaults to today. Future dates are rejected.
    """
    current = today or utc_today()
    day = selected or current
    if day > current:
        raise ValueError('Date cannot be in the future')
    return day


def start_of_day_utc(value: date) -> str:
    return datetime.combine(value, time.min, tzinfo=timezone.utc).isoformat()


def start_of_next_day_utc(value: date) -> str:
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=timezone.utc).isoformat()


def period_bounds(period: ReportPeriod, today: date | None = None) -> tuple[date, date]:
    current = today or utc_today()
    if period == ReportPeriod.TODAY:
        return current, current
    if period == ReportPeriod.LAST_7_DAYS:
        return current - timedelta(days=6), current
    if period == ReportPeriod.LAST_30_DAYS:
        return current - timedelta(days=29), current
    raise ValueError('Custom date range requires start_date and end_date.')


def resolve_report_bounds(
    period: ReportPeriod,
    start_date: date | None = None,
    end_date: date | None = None,
    today: date | None = None,
) -> tuple[date, date]:
    """Inclusive UTC calendar-day window for a report request."""
    if period != ReportPeriod.CUSTOM:
        return period_bounds(period, today)
    if start_date is None:
        raise ValueError(START_DATE_REQUIRED)
    if end_date is None:
        raise ValueError(END_DATE_REQUIRED)
    if start_date > end_date:
        raise ValueError(START_AFTER_END)
    return start_date, end_date


def chart_days(
    period: ReportPeriod,
    today: date | None = None,
    *,
    start: date | None = None,
    end: date | None = None,
) -> list[date]:
    """Daily chart series: 1 bar for Today, at most 7 bars otherwise (POC).

    Custom ranges plot every inclusive UTC day between start and end.
    """
    current = today or utc_today()
    if period == ReportPeriod.CUSTOM:
        if start is None or end is None:
            raise ValueError('Custom date range requires start_date and end_date.')
        days: list[date] = []
        day = start
        while day <= end:
            days.append(day)
            day += timedelta(days=1)
        return days
    if period == ReportPeriod.TODAY:
        return [current]
    return [current - timedelta(days=offset) for offset in range(6, -1, -1)]
