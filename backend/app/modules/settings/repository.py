from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.supabase import get_supabase

GST_COLUMNS = 'id, rate, is_active, created_at, updated_at'
OFFER_COLUMNS = (
    'id, name, description, discount_type, discount_value, is_active, '
    'valid_from, valid_to, franchise_id, promotion_id, created_by, created_at, updated_at'
)
PROMOTION_COLUMNS = (
    'id, name, description, promo_code, valid_from, valid_to, is_active, '
    'created_by, created_at, updated_at'
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

    def list_offers_for_franchise(self, franchise_id: UUID) -> list[dict[str, Any]]:
        response = (
            self._db.table('discounts')
            .select(OFFER_COLUMNS)
            .eq('franchise_id', str(franchise_id))
            .order('name')
            .execute()
        )
        return list(response.data or [])

    def list_promotions(self) -> list[dict[str, Any]]:
        response = (
            self._db.table('promotions')
            .select(PROMOTION_COLUMNS)
            .order('name')
            .execute()
        )
        return list(response.data or [])

    def get_promotion(self, promotion_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('promotions')
            .select(PROMOTION_COLUMNS)
            .eq('id', str(promotion_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def get_promotion_by_code(self, promo_code: str) -> dict[str, Any] | None:
        response = (
            self._db.table('promotions')
            .select(PROMOTION_COLUMNS)
            .ilike('promo_code', promo_code.strip())
            .limit(20)
            .execute()
        )
        needle = promo_code.strip().lower()
        for row in response.data or []:
            if str(row.get('promo_code') or '').lower() == needle:
                return row
        return None

    def create_promotion(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._db.table('promotions').insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError('Promotion was not created')
        return rows[0]

    def update_promotion(self, promotion_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._db.table('promotions')
            .update(payload)
            .eq('id', str(promotion_id))
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError('Promotion was not updated')
        return rows[0]

    def list_promotion_franchises(self, promotion_id: UUID) -> list[str]:
        response = (
            self._db.table('promotion_franchises')
            .select('franchise_id')
            .eq('promotion_id', str(promotion_id))
            .execute()
        )
        return [str(row['franchise_id']) for row in (response.data or []) if row.get('franchise_id')]

    def list_promotion_franchise_map(self, promotion_ids: list[str]) -> dict[str, list[str]]:
        unique_ids = [pid for pid in dict.fromkeys(promotion_ids) if pid]
        if not unique_ids:
            return {}
        response = (
            self._db.table('promotion_franchises')
            .select('promotion_id, franchise_id')
            .in_('promotion_id', unique_ids)
            .execute()
        )
        mapping: dict[str, list[str]] = {pid: [] for pid in unique_ids}
        for row in response.data or []:
            mapping.setdefault(str(row['promotion_id']), []).append(str(row['franchise_id']))
        return mapping

    def replace_promotion_franchises(self, promotion_id: UUID, franchise_ids: list[UUID]) -> None:
        self._db.table('promotion_franchises').delete().eq(
            'promotion_id', str(promotion_id)
        ).execute()
        if not franchise_ids:
            return
        payload = [
            {'promotion_id': str(promotion_id), 'franchise_id': str(fid)}
            for fid in franchise_ids
        ]
        self._db.table('promotion_franchises').insert(payload).execute()

    def franchise_participates(self, promotion_id: UUID, franchise_id: UUID) -> bool:
        response = (
            self._db.table('promotion_franchises')
            .select('id')
            .eq('promotion_id', str(promotion_id))
            .eq('franchise_id', str(franchise_id))
            .limit(1)
            .execute()
        )
        return bool(response.data)

    def franchise_exists(self, franchise_id: UUID) -> bool:
        response = (
            self._db.table('franchises')
            .select('id')
            .eq('id', str(franchise_id))
            .limit(1)
            .execute()
        )
        return bool(response.data)
