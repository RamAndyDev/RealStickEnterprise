from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.db.supabase import get_supabase

AUDIT_COLUMNS = (
    'id, franchise_id, franchise_name_snapshot, audit_date, auditor_id, '
    'auditor_name_snapshot, overall_status, remarks, created_at, updated_at'
)

ITEM_COLUMNS = (
    'id, audit_id, item_key, checklist_item, display_order, status, remarks, created_at'
)

LIST_COLUMNS = (
    'id, franchise_id, franchise_name_snapshot, audit_date, auditor_id, '
    'auditor_name_snapshot, overall_status, created_at'
)


class AuditsRepository:
    def __init__(self) -> None:
        self._db = get_supabase()

    def list_audits(
        self,
        *,
        franchise_id: UUID | None,
        from_date: date | None,
        to_date: date | None,
        overall_status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        query = self._db.table('franchise_audits').select(LIST_COLUMNS, count='exact')
        if franchise_id is not None:
            query = query.eq('franchise_id', str(franchise_id))
        if from_date is not None:
            query = query.gte('audit_date', from_date.isoformat())
        if to_date is not None:
            query = query.lte('audit_date', to_date.isoformat())
        if overall_status:
            query = query.eq('overall_status', overall_status)

        start = (page - 1) * page_size
        end = start + page_size - 1
        response = (
            query.order('audit_date', desc=True)
            .order('created_at', desc=True)
            .range(start, end)
            .execute()
        )
        rows = list(response.data or [])
        total = response.count
        if total is None:
            total = len(rows)
        return rows, int(total)

    def get_audit(self, audit_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('franchise_audits')
            .select(AUDIT_COLUMNS)
            .eq('id', str(audit_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def list_items(self, audit_id: UUID) -> list[dict[str, Any]]:
        response = (
            self._db.table('franchise_audit_items')
            .select(ITEM_COLUMNS)
            .eq('audit_id', str(audit_id))
            .order('display_order')
            .execute()
        )
        return list(response.data or [])

    def get_franchise(self, franchise_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('franchises')
            .select('id, name')
            .eq('id', str(franchise_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def create_audit_with_items(
        self,
        audit_payload: dict[str, Any],
        item_payloads: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Insert parent + items together. Roll back the parent if items fail."""
        created = self._insert_audit(audit_payload)
        audit_id = created['id']
        for item in item_payloads:
            item['audit_id'] = str(audit_id)
        try:
            items = self._insert_items(item_payloads)
        except Exception:
            self._delete_audit(audit_id)
            raise
        return created, items

    def _insert_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._db.table('franchise_audits')
            .insert(payload)
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError('Failed to create franchise audit')
        return rows[0]

    def _insert_items(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        response = (
            self._db.table('franchise_audit_items')
            .insert(payloads)
            .execute()
        )
        rows = list(response.data or [])
        if len(rows) != len(payloads):
            raise RuntimeError('Failed to create franchise audit items')
        return rows

    def _delete_audit(self, audit_id: UUID | str) -> None:
        self._db.table('franchise_audits').delete().eq('id', str(audit_id)).execute()
