from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.pos.schemas import PosOrder, PosOrderItem, PosPaymentMethod

__all__ = ['PosOrder', 'PosOrderItem', 'PosPaymentMethod', 'BillListItem', 'BillListResponse']


class BillListItem(BaseModel):
    id: UUID
    bill_number: str
    franchise_id: UUID
    franchise_name: str | None = None
    cashier_id: UUID | None = None
    cashier_name: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    total_amount: float
    payment_method: str | None = None


class BillListResponse(BaseModel):
    items: list[BillListItem]
    page: int
    page_size: int
    total: int = Field(ge=0)
