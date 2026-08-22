from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.validation import strip_text, validate_price, validate_required_text


def _strip_text(value: object) -> str | None:
    return strip_text(value)


def _require_non_negative(value: object, *, field_name: str) -> Decimal:
    amount = validate_price(value, field_name=field_name, allow_zero=True)
    assert amount is not None
    return amount


def _require_positive_selling_price(value: object) -> Decimal:
    amount = validate_price(
        value,
        field_name='Selling price',
        allow_zero=False,
    )
    assert amount is not None
    return amount


def _sanitize_client_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Strip reserved image/emoji keys — images are managed only via upload endpoints."""
    cleaned = dict(metadata or {})
    for key in ('image_url', 'image_path', 'emoji'):
        cleaned.pop(key, None)
    return cleaned


# ── Categories ──────────────────────────────────────────────────────────────


class ProductCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator('name', mode='before')
    @classmethod
    def require_name(cls, value: object) -> str:
        return validate_required_text(value, field_name='Category name', max_length=120)


class ProductCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    display_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator('name', mode='before')
    @classmethod
    def strip_name(cls, value: object) -> str | None:
        if value is None:
            return None
        return validate_required_text(value, field_name='Category name', max_length=120)


class ProductCategoryListResponse(BaseModel):
    items: list[ProductCategory]
    total: int


# ── Products ────────────────────────────────────────────────────────────────


class ProductCategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    display_order: int
    is_active: bool


class Product(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID | None
    sku: str | None = None
    name: str
    description: str | None = None
    image_url: str | None = None
    price: float
    min_price: float | None = None
    max_price: float | None = None
    is_active: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    category: ProductCategorySummary | None = None


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category_id: UUID
    description: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(ge=0)
    sku: str | None = Field(default=None, max_length=80)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator('name', mode='before')
    @classmethod
    def require_name(cls, value: object) -> str:
        return validate_required_text(value, field_name='Product name', max_length=200)

    @field_validator('description', 'sku', mode='before')
    @classmethod
    def strip_optional(cls, value: object) -> str | None:
        return _strip_text(value)

    @field_validator('price', mode='before')
    @classmethod
    def validate_price(cls, value: object) -> Decimal:
        if value is None or value == '':
            raise ValueError('Master price is required')
        return _require_non_negative(value, field_name='price')  # type: ignore[arg-type]

    @field_validator('min_price', 'max_price', mode='before')
    @classmethod
    def validate_optional_price(cls, value: object) -> Decimal | None:
        if value is None or value == '':
            return None
        return _require_non_negative(value, field_name='price')  # type: ignore[arg-type]

    @model_validator(mode='after')
    def bounds_and_metadata(self) -> ProductCreate:
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError('min_price cannot exceed max_price')
        self.metadata = _sanitize_client_metadata(self.metadata)
        return self


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: UUID | None = None
    description: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, ge=0)
    sku: str | None = Field(default=None, max_length=80)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None

    @field_validator('name', mode='before')
    @classmethod
    def strip_name(cls, value: object) -> str | None:
        if value is None:
            return None
        return validate_required_text(value, field_name='Product name', max_length=200)

    @field_validator('description', 'sku', mode='before')
    @classmethod
    def strip_optional(cls, value: object) -> str | None:
        return _strip_text(value)

    @field_validator('price', 'min_price', 'max_price', mode='before')
    @classmethod
    def validate_optional_price(cls, value: object) -> Decimal | None:
        if value is None or value == '':
            return None
        return _require_non_negative(value, field_name='price')  # type: ignore[arg-type]

    @model_validator(mode='after')
    def bounds_check(self) -> ProductUpdate:
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError('min_price cannot exceed max_price')
        if self.metadata is not None:
            self.metadata = _sanitize_client_metadata(self.metadata)
        return self


class ProductListResponse(BaseModel):
    items: list[Product]
    total: int


# ── Franchise product assignments ───────────────────────────────────────────


class FranchiseProductAssignment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    franchise_id: UUID
    product_id: UUID
    selling_price: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    product_name: str | None = None
    product_description: str | None = None
    product_is_active: bool | None = None
    master_price: float | None = None
    category_id: UUID | None = None
    category_name: str | None = None
    image_url: str | None = None
    category_is_active: bool | None = None
    available_for_pos: bool = False
    price_editable: bool = False


class FranchiseProductAssign(BaseModel):
    product_id: UUID
    selling_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    is_active: bool = True

    @field_validator('selling_price', mode='before')
    @classmethod
    def validate_selling_price(cls, value: object) -> Decimal:
        if value is None or value == '':
            raise ValueError('Franchise selling price is required')
        return _require_positive_selling_price(value)  # type: ignore[arg-type]


class FranchiseProductUpdate(BaseModel):
    selling_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    is_active: bool | None = None

    @field_validator('selling_price', mode='before')
    @classmethod
    def validate_selling_price(cls, value: object) -> Decimal | None:
        if value is None or value == '':
            return None
        return _require_positive_selling_price(value)  # type: ignore[arg-type]

    @model_validator(mode='after')
    def require_field(self) -> FranchiseProductUpdate:
        if self.selling_price is None and self.is_active is None:
            raise ValueError('Provide selling_price and/or is_active')
        return self


class OwnerFranchiseProductUpdate(BaseModel):
    """Franchise Owner may change selling_price only. Activation fields are rejected."""

    model_config = ConfigDict(extra='forbid')

    selling_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    @field_validator('selling_price', mode='before')
    @classmethod
    def validate_selling_price(cls, value: object) -> Decimal:
        if value is None or value == '':
            raise ValueError('Franchise selling price is required')
        return _require_positive_selling_price(value)  # type: ignore[arg-type]


class FranchiseProductListResponse(BaseModel):
    items: list[FranchiseProductAssignment]
    total: int
