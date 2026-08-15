from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.roles import UserRole
from app.core.security import CurrentProfile, require_role
from app.modules.gallery.schemas import (
    AdminGalleryItem,
    AdminGalleryListResponse,
    GalleryCreate,
    GalleryUpdate,
    PublicGalleryListResponse,
)
from app.modules.gallery.service import GalleryService

admin_router = APIRouter(prefix='/admin/gallery', tags=['admin-gallery'])
public_router = APIRouter(prefix='/public', tags=['public'])

SystemAdmin = Annotated[CurrentProfile, Depends(require_role(UserRole.SYSTEM_ADMIN))]


def get_gallery_service() -> GalleryService:
    return GalleryService()


@admin_router.get('', response_model=AdminGalleryListResponse)
def list_admin_gallery(
    _: SystemAdmin,
    service: GalleryService = Depends(get_gallery_service),
) -> AdminGalleryListResponse:
    return service.list_admin()


@admin_router.post('', response_model=AdminGalleryItem, status_code=201)
def create_gallery_item(
    body: GalleryCreate,
    profile: SystemAdmin,
    service: GalleryService = Depends(get_gallery_service),
) -> AdminGalleryItem:
    return service.create(body, uploaded_by=profile.id)


@admin_router.patch('/{item_id}', response_model=AdminGalleryItem)
def update_gallery_item(
    item_id: UUID,
    body: GalleryUpdate,
    _: SystemAdmin,
    service: GalleryService = Depends(get_gallery_service),
) -> AdminGalleryItem:
    return service.update(item_id, body)


@admin_router.post('/{item_id}/media', response_model=AdminGalleryItem)
async def upload_gallery_media(
    item_id: UUID,
    _: SystemAdmin,
    file: UploadFile = File(...),
    service: GalleryService = Depends(get_gallery_service),
) -> AdminGalleryItem:
    return await service.upload_media(item_id, file)


@public_router.get('/gallery', response_model=PublicGalleryListResponse)
def list_public_gallery(
    service: GalleryService = Depends(get_gallery_service),
) -> PublicGalleryListResponse:
    return service.list_public()
