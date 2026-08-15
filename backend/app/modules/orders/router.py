from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.roles import UserRole
from app.core.security import CurrentProfile, require_role
from app.modules.orders.schemas import BillListResponse
from app.modules.orders.service import OrdersService
from app.modules.pos.schemas import PosOrder, PosPaymentMethod

router = APIRouter(prefix='/orders', tags=['orders'])

BillsUser = Annotated[
    CurrentProfile,
    Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.FRANCHISE_OWNER, UserRole.EMPLOYEE)),
]


def get_orders_service() -> OrdersService:
    return OrdersService()


@router.get('', response_model=BillListResponse)
def list_completed_orders(
    profile: BillsUser,
    franchise_id: UUID | None = Query(default=None),
    bill_number: str | None = Query(default=None, max_length=40),
    payment_method: PosPaymentMethod | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: OrdersService = Depends(get_orders_service),
) -> BillListResponse:
    return service.list_bills(
        profile,
        franchise_id=franchise_id,
        bill_number=bill_number,
        payment_method=payment_method,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.get('/{order_id}', response_model=PosOrder)
def get_completed_order(
    order_id: UUID,
    profile: BillsUser,
    service: OrdersService = Depends(get_orders_service),
) -> PosOrder:
    return service.get_bill(profile, order_id)
