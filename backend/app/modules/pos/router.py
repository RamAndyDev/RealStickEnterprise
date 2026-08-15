from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.roles import UserRole
from app.core.security import CurrentProfile, require_role
from app.modules.pos.schemas import PosMenuResponse, PosOfferListResponse, PosOrder, PosOrderCreate
from app.modules.pos.service import PosService

router = APIRouter(prefix='/pos', tags=['pos'])

PosUser = Annotated[
    CurrentProfile,
    Depends(require_role(UserRole.EMPLOYEE)),
]


def get_pos_service() -> PosService:
    return PosService()


@router.get('/menu', response_model=PosMenuResponse)
def get_pos_menu(
    profile: PosUser,
    service: PosService = Depends(get_pos_service),
) -> PosMenuResponse:
    return service.get_menu(profile)


@router.get('/offers', response_model=PosOfferListResponse)
def get_pos_offers(
    profile: PosUser,
    service: PosService = Depends(get_pos_service),
) -> PosOfferListResponse:
    return service.list_offers(profile)


@router.post('/orders', response_model=PosOrder, status_code=201)
def create_pos_order(
    body: PosOrderCreate,
    profile: PosUser,
    service: PosService = Depends(get_pos_service),
) -> PosOrder:
    return service.complete_order(profile, body)


@router.get('/orders/{order_id}', response_model=PosOrder)
def get_pos_order(
    order_id: UUID,
    profile: PosUser,
    service: PosService = Depends(get_pos_service),
) -> PosOrder:
    return service.get_order(profile, order_id)
