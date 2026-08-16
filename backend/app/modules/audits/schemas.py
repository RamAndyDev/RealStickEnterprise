from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FranchiseAuditStatus(StrEnum):
    PASS = 'PASS'
    NEEDS_ATTENTION = 'NEEDS_ATTENTION'
    FAIL = 'FAIL'


def _strip_optional(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError('value must be a string')
    stripped = value.strip()
    return stripped or None


class AuditItemInput(BaseModel):
    model_config = ConfigDict(extra='ignore')

    item_key: str = Field(min_length=1, max_length=80)
    status: FranchiseAuditStatus
    remarks: str | None = None

    @field_validator('item_key')
    @classmethod
    def strip_item_key(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError('item_key is required')
        return stripped

    @field_validator('remarks')
    @classmethod
    def strip_remarks(cls, value: object) -> str | None:
        return _strip_optional(value)


class AuditCreate(BaseModel):
    """Client create payload. overall_status and auditor_* are ignored if sent."""

    model_config = ConfigDict(extra='ignore')

    franchise_id: UUID | None = None
    audit_date: date
    remarks: str | None = None
    items: list[AuditItemInput]

    @field_validator('remarks')
    @classmethod
    def strip_remarks(cls, value: object) -> str | None:
        return _strip_optional(value)


class AuditItem(BaseModel):
    id: UUID
    item_key: str
    checklist_item: str
    display_order: int
    status: FranchiseAuditStatus
    remarks: str | None = None


class AuditListItem(BaseModel):
    id: UUID
    franchise_id: UUID
    franchise_name: str
    audit_date: date
    auditor_id: UUID | None = None
    auditor_name: str
    overall_status: FranchiseAuditStatus
    created_at: datetime


class AuditListResponse(BaseModel):
    items: list[AuditListItem]
    page: int
    page_size: int
    total: int = Field(ge=0)


class AuditDetail(BaseModel):
    id: UUID
    franchise_id: UUID
    franchise_name: str
    audit_date: date
    auditor_id: UUID | None = None
    auditor_name: str
    overall_status: FranchiseAuditStatus
    remarks: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[AuditItem]
