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
    return current - timedelta(days=29), current


def chart_days(period: ReportPeriod, today: date | None = None) -> list[date]:
    """Daily chart series: 1 bar for Today, at most 7 bars otherwise (POC)."""
    current = today or utc_today()
    if period == ReportPeriod.TODAY:
        return [current]
    return [current - timedelta(days=offset) for offset in range(6, -1, -1)]
