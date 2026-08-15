from __future__ import annotations

from typing import Any

from app.db.supabase import get_supabase

PUBLIC_CATEGORY_COLUMNS = 'id, name, display_order, is_active'
PUBLIC_PRODUCT_COLUMNS = 'id, category_id, name, description, image_url, is_active'


class PublicCatalogRepository:
    def __init__(self) -> None:
        self._db = get_supabase()

    def list_active_categories(self) -> list[dict[str, Any]]:
        response = (
            self._db.table('product_categories')
            .select(PUBLIC_CATEGORY_COLUMNS)
            .eq('is_active', True)
            .order('display_order')
            .execute()
        )
        rows = list(response.data or [])
        rows.sort(key=lambda row: ((row.get('display_order') or 0), (row.get('name') or '')))
        return rows

    def list_active_products(self) -> list[dict[str, Any]]:
        response = (
            self._db.table('products')
            .select(PUBLIC_PRODUCT_COLUMNS)
            .eq('is_active', True)
            .execute()
        )
        rows = list(response.data or [])
        rows.sort(key=lambda row: (row.get('name') or ''))
        return rows
