from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.roles import UserRole
from app.core.security import CurrentProfile, require_role
from app.modules.settings.schemas import (
    GstSettings,
    GstUpdate,
    Offer,
    OfferCreate,
    OfferListResponse,
    OfferUpdate,
)
from app.modules.settings.service import SettingsService

router = APIRouter(prefix='/admin', tags=['admin-settings'])

SystemAdmin = Annotated[CurrentProfile, Depends(require_role(UserRole.SYSTEM_ADMIN))]


def get_settings_service() -> SettingsService:
    return SettingsService()


@router.get('/gst', response_model=GstSettings)
def get_gst(
    _: SystemAdmin,
    service: SettingsService = Depends(get_settings_service),
) -> GstSettings:
    return service.get_gst()


@router.patch('/gst', response_model=GstSettings)
def update_gst(
    body: GstUpdate,
    _: SystemAdmin,
    service: SettingsService = Depends(get_settings_service),
) -> GstSettings:
    return service.update_gst(body)


@router.get('/offers', response_model=OfferListResponse)
def list_offers(
    _: SystemAdmin,
    service: SettingsService = Depends(get_settings_service),
) -> OfferListResponse:
    return service.list_offers()


@router.post('/offers', response_model=Offer, status_code=201)
def create_offer(
    body: OfferCreate,
    _: SystemAdmin,
    service: SettingsService = Depends(get_settings_service),
) -> Offer:
    return service.create_offer(body)


@router.patch('/offers/{offer_id}', response_model=Offer)
def update_offer(
    offer_id: UUID,
    body: OfferUpdate,
    _: SystemAdmin,
    service: SettingsService = Depends(get_settings_service),
) -> Offer:
    return service.update_offer(offer_id, body)
