from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.supabase import get_supabase
from app.modules.products.constants import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    ALLOWED_IMAGE_EXTENSIONS,
    PRODUCT_IMAGE_MAX_BYTES,
)

GALLERY_BUCKET = 'gallery'
GALLERY_IMAGE_MAX_BYTES = PRODUCT_IMAGE_MAX_BYTES
GALLERY_ALLOWED_CONTENT_TYPES = ALLOWED_IMAGE_CONTENT_TYPES
GALLERY_ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS

ADMIN_COLUMNS = (
    'id, title, caption, author_name, media_type, media_url, storage_path, '
    'display_order, is_approved, is_archived, created_at, updated_at'
)
PUBLIC_COLUMNS = (
    'id, title, caption, author_name, media_type, media_url, display_order, '
    'is_approved, is_archived, created_at'
)


class GalleryRepository:
    def __init__(self) -> None:
        self._db = get_supabase()

    def list_admin_items(self) -> list[dict[str, Any]]:
        response = self._db.table('gallery_items').select(ADMIN_COLUMNS).execute()
        rows = list(response.data or [])
        rows.sort(
            key=lambda row: (
                int(row.get('display_order') or 0),
                str(row.get('created_at') or ''),
            )
        )
        return rows

    def list_public_items(self) -> list[dict[str, Any]]:
        response = (
            self._db.table('gallery_items')
            .select(PUBLIC_COLUMNS)
            .eq('is_approved', True)
            .eq('is_archived', False)
            .execute()
        )
        rows = list(response.data or [])
        rows.sort(
            key=lambda row: (
                int(row.get('display_order') or 0),
                str(row.get('created_at') or ''),
            )
        )
        return rows

    def get_item(self, item_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('gallery_items')
            .select(ADMIN_COLUMNS)
            .eq('id', str(item_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def create_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._db.table('gallery_items').insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError('Gallery insert returned no data')
        return rows[0]

    def update_item(self, item_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._db.table('gallery_items')
            .update(payload)
            .eq('id', str(item_id))
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError('Gallery update returned no data')
        return rows[0]

    def upload_image(self, *, path: str, content: bytes, content_type: str) -> str:
        bucket = self._db.storage.from_(GALLERY_BUCKET)
        bucket.upload(
            path,
            content,
            file_options={'content-type': content_type, 'upsert': 'true'},
        )
        return self.get_public_url(path)

    def remove_image(self, path: str) -> None:
        self._db.storage.from_(GALLERY_BUCKET).remove([path])

    def get_public_url(self, path: str) -> str:
        result = self._db.storage.from_(GALLERY_BUCKET).get_public_url(path)
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return str(result.get('publicUrl') or result.get('public_url') or '')
        public_url = getattr(result, 'public_url', None) or getattr(result, 'publicUrl', None)
        if public_url:
            return str(public_url)
        return str(result)
