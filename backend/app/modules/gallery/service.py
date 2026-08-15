from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from app.modules.gallery.repository import GalleryRepository
from app.modules.gallery.schemas import (
    AdminGalleryItem,
    AdminGalleryListResponse,
    GalleryCreate,
    GalleryUpdate,
    PublicGalleryItem,
    PublicGalleryListResponse,
    validate_external_video_url,
)
from app.modules.products.images import read_and_validate_image


def _to_admin(row: dict) -> AdminGalleryItem:
    return AdminGalleryItem.model_validate(row)


class GalleryService:
    def __init__(self, repo: GalleryRepository | None = None) -> None:
        self.repo = repo or GalleryRepository()

    def list_admin(self) -> AdminGalleryListResponse:
        items = [_to_admin(row) for row in self.repo.list_admin_items()]
        return AdminGalleryListResponse(items=items, total=len(items))

    def list_public(self) -> PublicGalleryListResponse:
        items = [PublicGalleryItem.model_validate(row) for row in self.repo.list_public_items()]
        return PublicGalleryListResponse(items=items, total=len(items))

    def create(self, body: GalleryCreate, uploaded_by: UUID) -> AdminGalleryItem:
        payload = {
            'franchise_id': None,
            'title': body.title,
            'caption': body.caption,
            'author_name': body.author_name if body.media_type == 'TESTIMONIAL' else None,
            'media_type': body.media_type,
            'storage_path': None,
            'media_url': body.media_url if body.media_type == 'VIDEO' else None,
            'display_order': body.display_order,
            'is_approved': body.is_approved,
            'is_archived': False,
            'uploaded_by': str(uploaded_by),
        }
        if body.media_type == 'IMAGE' and body.is_approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Upload an image before approving this item',
            )
        row = self.repo.create_item(payload)
        return _to_admin(row)

    def update(self, item_id: UUID, body: GalleryUpdate) -> AdminGalleryItem:
        existing = self.repo.get_item(item_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Gallery item not found')

        payload = body.model_dump(exclude_unset=True)
        media_type = existing.get('media_type')

        if 'media_url' in payload:
            if media_type != 'VIDEO':
                payload.pop('media_url', None)
            elif payload['media_url']:
                try:
                    payload['media_url'] = validate_external_video_url(payload['media_url'])
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=str(exc),
                    ) from exc

        if media_type == 'TESTIMONIAL':
            next_caption = payload['caption'] if 'caption' in payload else existing.get('caption')
            next_author = (
                payload['author_name'] if 'author_name' in payload else existing.get('author_name')
            )
            if not (next_caption or '').strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail='Testimonial quote is required',
                )
            if not (next_author or '').strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail='Testimonial author is required',
                )

        if payload.get('is_approved') is True and media_type == 'IMAGE' and not (
            payload.get('media_url') or existing.get('media_url')
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Upload an image before approving this item',
            )

        if not payload:
            return _to_admin(existing)
        row = self.repo.update_item(item_id, payload)
        return _to_admin(row)

    async def upload_media(self, item_id: UUID, file: UploadFile) -> AdminGalleryItem:
        existing = self.repo.get_item(item_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Gallery item not found')
        if existing.get('media_type') != 'IMAGE':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Media upload is only supported for images',
            )

        content, content_type, extension = await read_and_validate_image(file)
        path = f'{item_id}/{uuid4().hex}.{extension}'
        old_path = existing.get('storage_path')

        try:
            public_url = self.repo.upload_image(
                path=path,
                content=content,
                content_type=content_type,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to upload gallery image',
            ) from exc

        try:
            row = self.repo.update_item(
                item_id,
                {'storage_path': path, 'media_url': public_url},
            )
        except Exception as exc:
            self.repo.remove_image(path)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to save gallery image',
            ) from exc

        if old_path and old_path != path:
            try:
                self.repo.remove_image(old_path)
            except Exception:
                pass
        return _to_admin(row)
