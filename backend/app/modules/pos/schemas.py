from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validation import strip_text, validate_phone, validate_quantity


class PosPaymentMethod(StrEnum):
    CASH = 'CASH'
    UPI = 'UPI'
    CARD = 'CARD'


def _strip_text(value: object) -> str | None:
    return strip_text(value)


class PosMenuCategory(BaseModel):
    id: UUID
    name: str
    display_order: int


class PosMenuItem(BaseModel):
    product_id: UUID
    name: str
    description: str | None = None
    image_url: str | None = None
    category_id: UUID | None = None
    category_name: str | None = None
    selling_price: float
    available_for_pos: bool


class PosMenuResponse(BaseModel):
    franchise_id: UUID
    franchise_name: str | None = None
    gst_rate: float | None = None
    cgst_rate: float | None = None
    sgst_rate: float | None = None
    categories: list[PosMenuCategory]
    items: list[PosMenuItem]


class PosOffer(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    discount_type: str
    discount_value: float
    valid_from: datetime | None = None
    valid_to: datetime | None = None


class PosOfferListResponse(BaseModel):
    items: list[PosOffer]
    total: int


class PosOrderItemIn(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1, le=999)

    @field_validator('quantity', mode='before')
    @classmethod
    def require_quantity(cls, value: object) -> int:
        return validate_quantity(value, field_name='Quantity', minimum=1, maximum=999)


class PosOrderCreate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    items: list[PosOrderItemIn] = Field(min_length=1, max_length=100)
    payment_method: PosPaymentMethod
    customer_phone: str | None = Field(default=None, max_length=20)
    offer_id: UUID | None = None

    @field_validator('customer_phone', mode='before')
    @classmethod
    def strip_phone(cls, value: object) -> str | None:
        return validate_phone(value, required=False)


class PosOrderItem(BaseModel):
    id: UUID | None = None
    product_id: UUID
    product_name_snapshot: str
    unit_price: float
    quantity: int
    line_discount_amount: float = 0
    line_total: float


class PosOrder(BaseModel):
    id: UUID
    franchise_id: UUID
    bill_number: str
    status: str
    customer_phone: str | None = None
    subtotal: float
    discount_amount: float
    discount_percent: float | None = None
    discount_value: float | None = None
    discount_type: str | None = None
    offer_id: UUID | None = None
    offer_name: str | None = None
    taxable_amount: float
    gst_rate: float
    gst_amount: float
    cgst_rate: float
    sgst_rate: float
    cgst_amount: float
    sgst_amount: float
    total_amount: float
    payment_method: str | None = None
    cashier_id: UUID | None = None
    cashier_name: str | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    franchise_name: str | None = None
    franchise_address: str | None = None
    franchise_city: str | None = None
    franchise_state: str | None = None
    items: list[PosOrderItem] = Field(default_factory=list)
    payment_status: str | None = None
