from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.validation import (
    strip_text,
    validate_amount,
    validate_email,
    validate_optional_text,
    validate_phone,
    validate_required_text,
)

OWNER_EMAIL_EXISTS_DETAIL = 'Email already exists. Please use a different email address.'
FRANCHISE_DELETE_BLOCKED_DETAIL = (
    'This franchise cannot be deleted because it is already used in existing business records. '
    'Deactivate it instead.'
)


def _normalize_email(value: object) -> str | None:
    return validate_email(value, required=False)


def _strip_text(value: object) -> str | None:
    return strip_text(value)


class FranchiseStatus(StrEnum):
    APPLICATION = 'APPLICATION'
    PENDING_PAYMENT = 'PENDING_PAYMENT'
    SETUP = 'SETUP'
    ACTIVE = 'ACTIVE'
    SUSPENDED = 'SUSPENDED'
    CLOSED = 'CLOSED'


FRANCHISE_TIERS = frozenset({'Founder', 'Growth', 'Scale', 'Elite'})

# Stored as franchise_payments.payment_method (text). Distinct from POS CASH/UPI/CARD.
class FranchisePaymentMethod(StrEnum):
    CASH = 'CASH'
    BANK_TRANSFER = 'BANK_TRANSFER'
    UPI = 'UPI'
    CHEQUE = 'CHEQUE'
    OTHER = 'OTHER'


# Existing franchise_payments.status check constraint values.
class FranchisePaymentStatus(StrEnum):
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    REFUNDED = 'REFUNDED'


def _require_positive_paid_amount(value: object) -> Decimal:
    amount = validate_amount(value, field_name='Paid amount')
    assert amount is not None
    return amount


class FranchiseOwnerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    is_active: bool


class FranchiseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str | None = None
    owner_email: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    tier: str | None = None
    status: FranchiseStatus
    open_date: date | None = None
    closed_at: datetime | None = None
    employee_limit: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    owner: FranchiseOwnerSummary | None = None
    payment_status: str | None = None
    launch_progress_completed: int = 0
    launch_progress_total: int = 0


class FranchiseApplicationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    applicant_name: str
    email: str
    phone: str | None = None
    city: str | None = None
    state: str | None = None
    investment_range: str | None = None
    message: str | None = None
    status: str
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    converted_franchise_id: UUID | None = None


class FranchisePaymentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: float
    currency: str
    payment_method: str | None = None
    reference_number: str | None = None
    status: str
    paid_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class LaunchChecklistItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_key: str
    item_name: str
    display_order: int
    is_completed: bool
    completed_at: datetime | None = None
    completed_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class FranchiseDetail(FranchiseListItem):
    settings: dict = Field(default_factory=dict)
    applications: list[FranchiseApplicationSummary] = Field(default_factory=list)
    payments: list[FranchisePaymentSummary] = Field(default_factory=list)
    launch_checklist: list[LaunchChecklistItem] = Field(default_factory=list)


class FranchiseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=50)
    owner_email: str | None = None
    owner_full_name: str | None = Field(default=None, max_length=200)
    owner_phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=20)
    tier: str = Field(default='Founder')
    # Approved admin-created outlets start in SETUP (APPLICATION is for public enquiry).
    status: FranchiseStatus = FranchiseStatus.SETUP
    open_date: date | None = None
    employee_limit: int = Field(default=10, ge=1, le=10)

    @field_validator('name', mode='before')
    @classmethod
    def require_name(cls, value: object) -> str:
        return validate_required_text(value, field_name='Outlet name', max_length=200)

    @field_validator('code', 'address', 'city', 'state', 'postal_code', mode='before')
    @classmethod
    def strip_optional(cls, value: object) -> str | None:
        return _strip_text(value)

    @field_validator('owner_full_name', mode='before')
    @classmethod
    def strip_owner_name(cls, value: object) -> str | None:
        return validate_optional_text(value, field_name='Owner name', max_length=200)

    @field_validator('owner_phone', mode='before')
    @classmethod
    def validate_owner_phone(cls, value: object) -> str | None:
        return validate_phone(value, required=False)

    @field_validator('owner_email', mode='before')
    @classmethod
    def validate_owner_email(cls, value: object) -> str | None:
        return _normalize_email(value)

    @field_validator('tier')
    @classmethod
    def validate_tier(cls, value: str) -> str:
        if value not in FRANCHISE_TIERS:
            raise ValueError(f'tier must be one of: {", ".join(sorted(FRANCHISE_TIERS))}')
        return value

    @model_validator(mode='after')
    def require_owner_email_when_creating_owner(self) -> FranchiseCreate:
        if self.owner_full_name and not self.owner_email:
            raise ValueError('Owner email is required')
        return self

    def owner_create_payload(self) -> FranchiseOwnerCreate | None:
        if not self.owner_full_name:
            return None
        return FranchiseOwnerCreate(
            full_name=self.owner_full_name,
            email=self.owner_email or '',
            phone=self.owner_phone,
        )


class FranchiseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=50)
    owner_email: str | None = None
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=20)
    tier: str | None = None
    open_date: date | None = None
    employee_limit: int | None = Field(default=None, ge=1, le=10)
    is_archived: bool | None = None

    @field_validator('name', mode='before')
    @classmethod
    def strip_name(cls, value: object) -> str | None:
        if value is None:
            return None
        return validate_required_text(value, field_name='Outlet name', max_length=200)

    @field_validator('code', 'address', 'city', 'state', 'postal_code', mode='before')
    @classmethod
    def strip_optional(cls, value: object) -> str | None:
        return _strip_text(value)

    @field_validator('owner_email', mode='before')
    @classmethod
    def validate_owner_email(cls, value: object) -> str | None:
        return _normalize_email(value)

    @field_validator('tier')
    @classmethod
    def validate_tier(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in FRANCHISE_TIERS:
            raise ValueError(f'tier must be one of: {", ".join(sorted(FRANCHISE_TIERS))}')
        return value


class FranchiseStatusUpdate(BaseModel):
    status: FranchiseStatus


class FranchiseOwnerAssign(BaseModel):
    """Assign an existing profile as FRANCHISE_OWNER for this outlet."""

    owner_profile_id: UUID | None = None
    owner_email: str | None = None

    @field_validator('owner_email', mode='before')
    @classmethod
    def validate_email(cls, value: object) -> str | None:
        return _normalize_email(value)

    @model_validator(mode='after')
    def require_identifier(self) -> FranchiseOwnerAssign:
        if self.owner_profile_id is None and self.owner_email is None:
            raise ValueError('Provide owner_profile_id or owner_email')
        return self


class FranchiseOwnerCreate(BaseModel):
    """Create Auth user + FRANCHISE_OWNER profile and assign to this outlet."""

    full_name: str = Field(min_length=1, max_length=200)
    email: str
    phone: str | None = Field(default=None, max_length=40)

    @field_validator('full_name', mode='before')
    @classmethod
    def require_name(cls, value: object) -> str:
        return validate_required_text(value, field_name='Owner name', max_length=200)

    @field_validator('email', mode='before')
    @classmethod
    def require_email(cls, value: object) -> str:
        normalized = validate_email(value, required=True)
        if not normalized:
            raise ValueError('Owner email is required')
        return normalized

    @field_validator('phone', mode='before')
    @classmethod
    def strip_phone(cls, value: object) -> str | None:
        return validate_phone(value, required=False)


class FranchiseOwnerCreateResponse(BaseModel):
    franchise: FranchiseDetail
    owner: FranchiseOwnerSummary
    password_setup: str
    message: str


class LaunchChecklistItemUpdate(BaseModel):
    is_completed: bool


class FranchiseOfflinePaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    paid_at: date
    payment_method: FranchisePaymentMethod
    reference_number: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator('amount', mode='before')
    @classmethod
    def validate_amount(cls, value: object) -> Decimal:
        return _require_positive_paid_amount(value)

    @field_validator('reference_number', 'notes', mode='before')
    @classmethod
    def strip_optional(cls, value: object) -> str | None:
        return _strip_text(value)


class FranchiseListResponse(BaseModel):
    items: list[FranchiseListItem]
    total: int


class ApplicationListResponse(BaseModel):
    items: list[FranchiseApplicationSummary]
    total: int
