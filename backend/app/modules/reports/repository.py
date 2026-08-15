from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.db.supabase import get_supabase
from app.modules.reports.dates import start_of_day_utc, start_of_next_day_utc

ORDER_COLUMNS = (
    'id, franchise_id, bill_number, status, total_amount, payment_method, completed_at, created_at'
)
ITEM_COLUMNS = 'order_id, product_name_snapshot, quantity, unit_price, line_total'
FRANCHISE_COLUMNS = 'id, name, status, is_archived, city, tier'
PAGE_SIZE = 1000


class ReportsRepository:
    def __init__(self) -> None:
        self._db = get_supabase()

    def list_completed_orders(
        self,
        *,
        franchise_id: UUID | None,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        start = 0
        while True:
            query = self._db.table('orders').select(ORDER_COLUMNS).eq('status', 'COMPLETED')
            if franchise_id is not None:
                query = query.eq('franchise_id', str(franchise_id))
            if from_date is not None:
                query = query.gte('completed_at', start_of_day_utc(from_date))
            if to_date is not None:
                query = query.lt('completed_at', start_of_next_day_utc(to_date))
            response = query.order('completed_at', desc=True).range(start, start + PAGE_SIZE - 1).execute()
            chunk = list(response.data or [])
            rows.extend(chunk)
            if len(chunk) < PAGE_SIZE:
                break
            start += PAGE_SIZE
        return rows

    def list_order_items(self, order_ids: list[str]) -> list[dict[str, Any]]:
        if not order_ids:
            return []
        rows: list[dict[str, Any]] = []
        for offset in range(0, len(order_ids), PAGE_SIZE):
            batch = order_ids[offset : offset + PAGE_SIZE]
            response = (
                self._db.table('order_items')
                .select(ITEM_COLUMNS)
                .in_('order_id', batch)
                .execute()
            )
            rows.extend(list(response.data or []))
        return rows

    def list_franchises(self) -> list[dict[str, Any]]:
        response = (
            self._db.table('franchises')
            .select(FRANCHISE_COLUMNS)
            .eq('is_archived', False)
            .order('name')
            .execute()
        )
        return list(response.data or [])

    def get_franchise(self, franchise_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('franchises')
            .select(FRANCHISE_COLUMNS)
            .eq('id', str(franchise_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def count_active_outlets(self) -> int:
        response = (
            self._db.table('franchises')
            .select('id', count='exact')
            .eq('status', 'ACTIVE')
            .execute()
        )
        if response.count is not None:
            return int(response.count)
        return len(response.data or [])
