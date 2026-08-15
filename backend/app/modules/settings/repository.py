from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.supabase import get_supabase

GST_COLUMNS = 'id, rate, is_active, created_at, updated_at'
OFFER_COLUMNS = (
    'id, name, description, discount_type, discount_value, is_active, '
    'valid_from, valid_to, franchise_id, created_at, updated_at'
)


class SettingsRepository:
    def __init__(self) -> None:
        self._db = get_supabase()

    def get_active_gst(self) -> dict[str, Any] | None:
        response = (
            self._db.table('gst_settings')
            .select(GST_COLUMNS)
            .eq('is_active', True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def update_gst(self, gst_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._db.table('gst_settings')
            .update(payload)
            .eq('id', str(gst_id))
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError('GST settings were not updated')
        return rows[0]

    def create_gst(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._db.table('gst_settings').insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError('GST settings were not created')
        return rows[0]

    def list_offers(self) -> list[dict[str, Any]]:
        response = (
            self._db.table('discounts')
            .select(OFFER_COLUMNS)
            .order('name')
            .execute()
        )
        return list(response.data or [])

    def get_offer(self, offer_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('discounts')
            .select(OFFER_COLUMNS)
            .eq('id', str(offer_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def create_offer(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._db.table('discounts').insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError('Offer was not created')
        return rows[0]

    def update_offer(self, offer_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._db.table('discounts')
            .update(payload)
            .eq('id', str(offer_id))
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError('Offer was not updated')
        return rows[0]

    def franchise_exists(self, franchise_id: UUID) -> bool:
        response = (
            self._db.table('franchises')
            .select('id')
            .eq('id', str(franchise_id))
            .limit(1)
            .execute()
        )
        return bool(response.data)
