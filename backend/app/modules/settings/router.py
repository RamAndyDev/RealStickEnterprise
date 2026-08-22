from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.roles import UserRole
from app.core.security import CurrentProfile, require_role
from app.modules.settings.schemas import (
    FranchiseAuditSetting,
    FranchiseAuditSettingUpdate,
    GstSettings,
    GstUpdate,
    Offer,
    OfferCreate,
    OfferListResponse,
    OfferUpdate,
    Promotion,
    PromotionCreate,
    PromotionListResponse,
    PromotionUpdate,
)
from app.modules.settings.service import SettingsService

router = APIRouter(prefix='/admin', tags=['admin-settings'])
owner_router = APIRouter(prefix='/owner', tags=['owner-offers'])

SystemAdmin = Annotated[CurrentProfile, Depends(require_role(UserRole.SYSTEM_ADMIN))]
FranchiseOwner = Annotated[CurrentProfile, Depends(require_role(UserRole.FRANCHISE_OWNER))]


def get_settings_service() -> SettingsService:
    return SettingsService()


@router.get('/settings/franchise-audit', response_model=FranchiseAuditSetting)
def get_franchise_audit_setting(
    _: SystemAdmin,
    service: SettingsService = Depends(get_settings_service),
) -> FranchiseAuditSetting:
    return service.get_franchise_audit_setting()


@router.patch('/settings/franchise-audit', response_model=FranchiseAuditSetting)
def update_franchise_audit_setting(
    body: FranchiseAuditSettingUpdate,
    _: SystemAdmin,
    service: SettingsService = Depends(get_settings_service),
) -> FranchiseAuditSetting:
    return service.update_franchise_audit_setting(body)


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


@router.get('/promotions', response_model=PromotionListResponse)
def list_promotions(
    _: SystemAdmin,
    service: SettingsService = Depends(get_settings_service),
) -> PromotionListResponse:
    return service.list_promotions()


@router.post('/promotions', response_model=Promotion, status_code=201)
def create_promotion(
    body: PromotionCreate,
    profile: SystemAdmin,
    service: SettingsService = Depends(get_settings_service),
) -> Promotion:
    return service.create_promotion(body, profile)


@router.patch('/promotions/{promotion_id}', response_model=Promotion)
def update_promotion(
    promotion_id: UUID,
    body: PromotionUpdate,
    _: SystemAdmin,
    service: SettingsService = Depends(get_settings_service),
) -> Promotion:
    return service.update_promotion(promotion_id, body)


@owner_router.get('/offers', response_model=OfferListResponse)
def list_owner_offers(
    profile: FranchiseOwner,
    service: SettingsService = Depends(get_settings_service),
) -> OfferListResponse:
    return service.list_owner_offers(profile)


@owner_router.post('/offers', response_model=Offer, status_code=201)
def create_owner_offer(
    body: OfferCreate,
    profile: FranchiseOwner,
    service: SettingsService = Depends(get_settings_service),
) -> Offer:
    return service.create_owner_offer(profile, body)


@owner_router.patch('/offers/{offer_id}', response_model=Offer)
def update_owner_offer(
    offer_id: UUID,
    body: OfferUpdate,
    profile: FranchiseOwner,
    service: SettingsService = Depends(get_settings_service),
) -> Offer:
    return service.update_owner_offer(profile, offer_id, body)


@owner_router.get('/promotions', response_model=PromotionListResponse)
def list_owner_promotions(
    profile: FranchiseOwner,
    service: SettingsService = Depends(get_settings_service),
) -> PromotionListResponse:
    return service.list_owner_promotions(profile)
