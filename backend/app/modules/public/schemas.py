from __future__ import annotations

from uuid import UUID

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _strip_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError('value must be a string')
    stripped = value.strip()
    return stripped or None


class PublicCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id: UUID
    name: str
    display_order: int


class PublicCategoryListResponse(BaseModel):
    items: list[PublicCategory]
    total: int


class PublicProduct(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id: UUID
    category_id: UUID
    category_name: str
    name: str
    description: str | None = None
    image_url: str | None = None


class PublicProductListResponse(BaseModel):
    items: list[PublicProduct]
    total: int


class EnquiryType(StrEnum):
    GENERAL = 'GENERAL'
    FRANCHISE = 'FRANCHISE'
    COMPLAINT = 'COMPLAINT'
    FEEDBACK = 'FEEDBACK'
    OTHER = 'OTHER'


ENQUIRY_TYPE_LABELS = {
    EnquiryType.GENERAL: 'General Enquiry',
    EnquiryType.FRANCHISE: 'Franchise Enquiry',
    EnquiryType.COMPLAINT: 'Complaint',
    EnquiryType.FEEDBACK: 'Feedback',
    EnquiryType.OTHER: 'Other',
}


class ContactEnquiryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=20)
    email: EmailStr
    message: str = Field(min_length=1, max_length=2000)
    enquiry_type: EnquiryType = EnquiryType.GENERAL
    website: str | None = Field(default=None, max_length=200)

    @field_validator('name', 'phone', 'message', mode='before')
    @classmethod
    def strip_required(cls, value: object) -> str:
        stripped = _strip_text(value)
        if not stripped:
            raise ValueError('This field is required')
        return stripped

    @field_validator('website', mode='before')
    @classmethod
    def strip_honeypot(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return str(value)
        stripped = value.strip()
        return stripped or None


class ContactEnquiryResponse(BaseModel):
    message: str


class PublicContactOptions(BaseModel):
    phone: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    whatsapp_url: str | None = None
    tel_url: str | None = None
    mailto_url: str | None = None
