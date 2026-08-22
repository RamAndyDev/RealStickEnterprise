from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.gst import GST_MAX_RATE, split_gst_rate


def _strip_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError('value must be a string')
    stripped = value.strip()
    return stripped or None


class GstSettings(BaseModel):
    id: UUID
    rate: float
    cgst_rate: float
    sgst_rate: float
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FranchiseAuditSetting(BaseModel):
    franchise_owner_audit_enabled: bool


class FranchiseAuditSettingUpdate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    franchise_owner_audit_enabled: bool


class GstUpdate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    rate: Decimal = Field(..., ge=0, le=GST_MAX_RATE, max_digits=5, decimal_places=2)

    @model_validator(mode='after')
    def require_even_split(self) -> 'GstUpdate':
        split_gst_rate(self.rate)
        return self


class OfferDiscountType(StrEnum):
    PERCENTAGE = 'PERCENTAGE'


class Offer(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    discount_type: OfferDiscountType
    discount_value: float
    is_active: bool
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    franchise_id: UUID | None = None
    promotion_id: UUID | None = None
    promotion_name: str | None = None
    promotion_promo_code: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OfferListResponse(BaseModel):
    items: list[Offer]
    total: int


class OfferCreate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    discount_type: OfferDiscountType = OfferDiscountType.PERCENTAGE
    discount_value: Decimal = Field(..., gt=0, le=100, max_digits=5, decimal_places=2)
    is_active: bool = True
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    franchise_id: UUID | None = None
    promotion_id: UUID | None = None

    @field_validator('name', mode='before')
    @classmethod
    def require_name(cls, value: object) -> str:
        stripped = _strip_text(value)
        if not stripped:
            raise ValueError('Offer name is required')
        return stripped

    @field_validator('description', mode='before')
    @classmethod
    def strip_description(cls, value: object) -> str | None:
        return _strip_text(value)

    @model_validator(mode='after')
    def validity_window(self) -> 'OfferCreate':
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError('valid_from must be on or before valid_to')
        return self


class OfferUpdate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    discount_type: OfferDiscountType | None = None
    discount_value: Decimal | None = Field(default=None, gt=0, le=100, max_digits=5, decimal_places=2)
    is_active: bool | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    franchise_id: UUID | None = None
    promotion_id: UUID | None = None
    clear_valid_from: bool = False
    clear_valid_to: bool = False
    clear_franchise_id: bool = False
    clear_promotion_id: bool = False

    @field_validator('name', mode='before')
    @classmethod
    def strip_name(cls, value: object) -> str | None:
        if value is None:
            return None
        stripped = _strip_text(value)
        if not stripped:
            raise ValueError('Offer name cannot be empty')
        return stripped

    @field_validator('description', mode='before')
    @classmethod
    def strip_description(cls, value: object) -> str | None:
        if value is None:
            return None
        return _strip_text(value)

    @model_validator(mode='after')
    def validity_window(self) -> 'OfferUpdate':
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError('valid_from must be on or before valid_to')
        return self


def offer_from_row(row: dict[str, Any]) -> Offer:
    return Offer(
        id=row['id'],
        name=row['name'],
        description=row.get('description'),
        discount_type=row.get('discount_type') or OfferDiscountType.PERCENTAGE,
        discount_value=float(row['discount_value']),
        is_active=bool(row.get('is_active', True)),
        valid_from=row.get('valid_from'),
        valid_to=row.get('valid_to'),
        franchise_id=row.get('franchise_id'),
        promotion_id=row.get('promotion_id'),
        promotion_name=row.get('promotion_name'),
        promotion_promo_code=row.get('promotion_promo_code'),
        created_at=row.get('created_at'),
        updated_at=row.get('updated_at'),
    )


class Promotion(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    promo_code: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool
    franchise_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PromotionListResponse(BaseModel):
    items: list[Promotion]
    total: int


class PromotionCreate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    promo_code: str = Field(min_length=1, max_length=40)
    is_active: bool = True
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    franchise_ids: list[UUID] = Field(default_factory=list)

    @field_validator('name', 'promo_code', mode='before')
    @classmethod
    def require_text(cls, value: object) -> str:
        stripped = _strip_text(value)
        if not stripped:
            raise ValueError('This field is required')
        return stripped

    @field_validator('description', mode='before')
    @classmethod
    def strip_description(cls, value: object) -> str | None:
        return _strip_text(value)

    @model_validator(mode='after')
    def validity_window(self) -> 'PromotionCreate':
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError('valid_from must be on or before valid_to')
        return self


class PromotionUpdate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    promo_code: str | None = Field(default=None, min_length=1, max_length=40)
    is_active: bool | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    franchise_ids: list[UUID] | None = None
    clear_valid_from: bool = False
    clear_valid_to: bool = False

    @field_validator('name', 'promo_code', mode='before')
    @classmethod
    def strip_text_field(cls, value: object) -> str | None:
        if value is None:
            return None
        stripped = _strip_text(value)
        if not stripped:
            raise ValueError('This field cannot be empty')
        return stripped

    @field_validator('description', mode='before')
    @classmethod
    def strip_description(cls, value: object) -> str | None:
        if value is None:
            return None
        return _strip_text(value)

    @model_validator(mode='after')
    def validity_window(self) -> 'PromotionUpdate':
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError('valid_from must be on or before valid_to')
        return self
