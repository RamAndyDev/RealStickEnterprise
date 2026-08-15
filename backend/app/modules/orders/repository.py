from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from app.db.supabase import get_supabase
from app.modules.pos.repository import ITEM_COLUMNS, ORDER_COLUMNS

LIST_COLUMNS = (
    'id, franchise_id, bill_number, status, total_amount, payment_method, '
    'cashier_id, completed_at, created_at'
)


def _start_of_day_utc(value: date) -> str:
    return datetime.combine(value, time.min, tzinfo=timezone.utc).isoformat()


def _start_of_next_day_utc(value: date) -> str:
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=timezone.utc).isoformat()


class OrdersRepository:
    def __init__(self) -> None:
        self._db = get_supabase()

    def list_completed_orders(
        self,
        *,
        franchise_id: UUID | None,
        bill_number: str | None,
        payment_method: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        query = (
            self._db.table('orders')
            .select(LIST_COLUMNS, count='exact')
            .eq('status', 'COMPLETED')
        )
        if franchise_id is not None:
            query = query.eq('franchise_id', str(franchise_id))
        if bill_number:
            query = query.ilike('bill_number', bill_number)
        if payment_method:
            query = query.eq('payment_method', payment_method)
        if from_date is not None:
            query = query.gte('completed_at', _start_of_day_utc(from_date))
        if to_date is not None:
            query = query.lt('completed_at', _start_of_next_day_utc(to_date))

        start = (page - 1) * page_size
        end = start + page_size - 1
        response = query.order('completed_at', desc=True).range(start, end).execute()
        rows = list(response.data or [])
        total = response.count
        if total is None:
            total = len(rows)
        return rows, int(total)

    def get_order(self, order_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('orders')
            .select(ORDER_COLUMNS)
            .eq('id', str(order_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def list_order_items(self, order_id: UUID) -> list[dict[str, Any]]:
        response = (
            self._db.table('order_items')
            .select(ITEM_COLUMNS)
            .eq('order_id', str(order_id))
            .execute()
        )
        return list(response.data or [])

    def get_franchise(self, franchise_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('franchises')
            .select('id, name, address, city, state, status, is_archived')
            .eq('id', str(franchise_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def get_profile(self, profile_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('profiles')
            .select('id, full_name, role, franchise_id, is_active')
            .eq('id', str(profile_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def list_profiles_by_ids(self, profile_ids: list[str]) -> list[dict[str, Any]]:
        if not profile_ids:
            return []
        response = (
            self._db.table('profiles')
            .select('id, full_name')
            .in_('id', profile_ids)
            .execute()
        )
        return list(response.data or [])

    def list_franchises_by_ids(self, franchise_ids: list[str]) -> list[dict[str, Any]]:
        if not franchise_ids:
            return []
        response = (
            self._db.table('franchises')
            .select('id, name')
            .in_('id', franchise_ids)
            .execute()
        )
        return list(response.data or [])
