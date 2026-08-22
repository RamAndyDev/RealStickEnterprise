from __future__ import annotations

from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError

from app.db.supabase import get_supabase
from app.modules.products.constants import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    PRODUCT_IMAGE_BUCKET,
    PRODUCT_IMAGE_MAX_BYTES,
)

CATEGORY_COLUMNS = (
    'id, name, display_order, is_active, created_at, updated_at'
)

PRODUCT_COLUMNS = (
    'id, category_id, sku, name, description, image_url, price, min_price, max_price, '
    'is_active, metadata, created_at, updated_at'
)

ASSIGNMENT_COLUMNS = (
    'id, franchise_id, product_id, selling_price, is_active, created_at, updated_at'
)


class ProductRepository:
    def __init__(self) -> None:
        self._db = get_supabase()

    # ── Categories ──────────────────────────────────────────────────────────

    def list_categories(self, *, include_inactive: bool = True) -> list[dict[str, Any]]:
        query = self._db.table('product_categories').select(CATEGORY_COLUMNS)
        if not include_inactive:
            query = query.eq('is_active', True)
        response = query.order('display_order').order('name').execute()
        return list(response.data or [])

    def get_category(self, category_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('product_categories')
            .select(CATEGORY_COLUMNS)
            .eq('id', str(category_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def get_category_by_name(self, name: str) -> dict[str, Any] | None:
        response = (
            self._db.table('product_categories')
            .select(CATEGORY_COLUMNS)
            .eq('name', name)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def find_category_by_name_ci(self, name: str) -> dict[str, Any] | None:
        """Case-insensitive name match across all categories."""
        needle = name.strip().lower()
        if not needle:
            return None
        for row in self.list_categories(include_inactive=True):
            if (row.get('name') or '').strip().lower() == needle:
                return row
        return None

    def create_category(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._db.table('product_categories').insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError('Category insert returned no data')
        return rows[0]

    def update_category(self, category_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._db.table('product_categories')
            .update(payload)
            .eq('id', str(category_id))
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError('Category update returned no data')
        return rows[0]

    def set_category_active(self, category_id: UUID, is_active: bool) -> dict[str, Any]:
        response = self._db.rpc(
            'set_product_category_active',
            {'p_category_id': str(category_id), 'p_is_active': is_active},
        ).execute()
        data = response.data
        if isinstance(data, list):
            if not data:
                raise RuntimeError('Category update returned no data')
            return data[0]
        if not data:
            raise RuntimeError('Category update returned no data')
        return data

    def count_products_for_category(self, category_id: UUID) -> int:
        response = (
            self._db.table('products')
            .select('id')
            .eq('category_id', str(category_id))
            .execute()
        )
        return len(response.data or [])

    def delete_category(self, category_id: UUID) -> bool:
        response = (
            self._db.table('product_categories')
            .delete()
            .eq('id', str(category_id))
            .execute()
        )
        return bool(response.data)

    # ── Products ────────────────────────────────────────────────────────────

    def list_products(
        self,
        *,
        category_id: UUID | None = None,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> list[dict[str, Any]]:
        query = self._db.table('products').select(PRODUCT_COLUMNS)
        if category_id is not None:
            query = query.eq('category_id', str(category_id))
        if is_active is not None:
            query = query.eq('is_active', is_active)
        response = query.order('name').execute()
        rows = list(response.data or [])
        if search:
            needle = search.strip().lower()
            rows = [
                row
                for row in rows
                if needle in (row.get('name') or '').lower()
                or needle in (row.get('description') or '').lower()
                or needle in (row.get('sku') or '').lower()
            ]
        return rows

    def get_product(self, product_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('products')
            .select(PRODUCT_COLUMNS)
            .eq('id', str(product_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def create_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._db.table('products').insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError('Product insert returned no data')
        return rows[0]

    def update_product(self, product_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._db.table('products')
            .update(payload)
            .eq('id', str(product_id))
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError('Product update returned no data')
        return rows[0]

    def delete_product(self, product_id: UUID) -> bool:
        response = (
            self._db.table('products')
            .delete()
            .eq('id', str(product_id))
            .execute()
        )
        return bool(response.data)

    def product_has_business_references(self, product_id: UUID) -> bool:
        """True when any business/historical row still points at this product.

        Direct FKs: franchise_product_prices, order_items, recipes.
        recipe_items hang off recipes (no product_id column).
        inventory_movements has no product_id FK; a movement tagged to this
        product via reference_id is still treated as a historical reference.
        """
        pid = str(product_id)
        if self._row_exists('franchise_product_prices', 'product_id', pid):
            return True
        if self._row_exists('order_items', 'product_id', pid):
            return True
        if self._row_exists('recipes', 'product_id', pid):
            # recipes.product_id is the FK; recipe_items hang off recipes and
            # have no product_id column, so a recipe is enough to block delete.
            return True
        if self._row_exists('inventory_movements', 'reference_id', pid):
            return True
        return False

    def _row_exists(self, table: str, column: str, value: str) -> bool:
        response = (
            self._db.table(table)
            .select('id')
            .eq(column, value)
            .limit(1)
            .execute()
        )
        return bool(response.data)

    def get_products_by_ids(self, product_ids: list[str]) -> list[dict[str, Any]]:
        if not product_ids:
            return []
        response = (
            self._db.table('products')
            .select(PRODUCT_COLUMNS)
            .in_('id', product_ids)
            .execute()
        )
        return list(response.data or [])

    # ── Franchise assignments ───────────────────────────────────────────────

    def list_franchise_products(self, franchise_id: UUID) -> list[dict[str, Any]]:
        response = (
            self._db.table('franchise_product_prices')
            .select(ASSIGNMENT_COLUMNS)
            .eq('franchise_id', str(franchise_id))
            .order('created_at', desc=True)
            .execute()
        )
        return list(response.data or [])

    def get_franchise_product(
        self,
        franchise_id: UUID,
        product_id: UUID,
    ) -> dict[str, Any] | None:
        response = (
            self._db.table('franchise_product_prices')
            .select(ASSIGNMENT_COLUMNS)
            .eq('franchise_id', str(franchise_id))
            .eq('product_id', str(product_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def list_franchise_prices_for_product(
        self,
        product_id: UUID,
        *,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        query = (
            self._db.table('franchise_product_prices')
            .select(ASSIGNMENT_COLUMNS)
            .eq('product_id', str(product_id))
        )
        if active_only:
            query = query.eq('is_active', True)
        response = query.execute()
        return list(response.data or [])

    def create_franchise_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._db.table('franchise_product_prices').insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError('Franchise product insert returned no data')
        return rows[0]

    def update_franchise_product(
        self,
        franchise_id: UUID,
        product_id: UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        response = (
            self._db.table('franchise_product_prices')
            .update(payload)
            .eq('franchise_id', str(franchise_id))
            .eq('product_id', str(product_id))
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def get_franchise(self, franchise_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('franchises')
            .select('id, name, is_archived')
            .eq('id', str(franchise_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    # ── Storage ─────────────────────────────────────────────────────────────

    def ensure_product_images_bucket(self) -> None:
        storage = self._db.storage
        getter = getattr(storage, 'get_bucket', None)
        creator = getattr(storage, 'create_bucket', None)
        if callable(getter):
            try:
                getter(PRODUCT_IMAGE_BUCKET)
                return
            except Exception:
                pass
        if callable(creator):
            try:
                creator(
                    PRODUCT_IMAGE_BUCKET,
                    {
                        'public': True,
                        'file_size_limit': PRODUCT_IMAGE_MAX_BYTES,
                        'allowed_mime_types': list(ALLOWED_IMAGE_CONTENT_TYPES),
                    },
                )
            except Exception:
                pass

    def upload_product_image(
        self,
        *,
        path: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """Upload to product-images bucket; returns public URL."""
        self.ensure_product_images_bucket()
        bucket = self._db.storage.from_(PRODUCT_IMAGE_BUCKET)
        bucket.upload(
            path,
            content,
            file_options={'content-type': content_type, 'upsert': 'true'},
        )
        return self.get_public_url(path)

    def remove_product_image(self, path: str) -> None:
        self._db.storage.from_(PRODUCT_IMAGE_BUCKET).remove([path])

    def get_public_url(self, path: str) -> str:
        result = self._db.storage.from_(PRODUCT_IMAGE_BUCKET).get_public_url(path)
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return str(result.get('publicUrl') or result.get('public_url') or '')
        public_url = getattr(result, 'public_url', None) or getattr(result, 'publicUrl', None)
        if public_url:
            return str(public_url)
        return str(result)

    @staticmethod
    def is_unique_violation(exc: Exception) -> bool:
        if isinstance(exc, APIError):
            code = getattr(exc, 'code', None) or ''
            message = str(exc)
            return code == '23505' or 'duplicate' in message.lower() or 'unique' in message.lower()
        message = str(exc).lower()
        return 'duplicate' in message or 'unique' in message

    @staticmethod
    def is_foreign_key_violation(exc: Exception) -> bool:
        if isinstance(exc, APIError):
            code = getattr(exc, 'code', None) or ''
            message = str(exc).lower()
            return code == '23503' or 'foreign key' in message
        return 'foreign key' in str(exc).lower()
