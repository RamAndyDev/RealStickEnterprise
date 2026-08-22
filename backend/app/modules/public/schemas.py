from __future__ import annotations

from uuid import UUID

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validation import strip_text, validate_email, validate_phone, validate_required_text


def _strip_text(value: object) -> str | None:
    return strip_text(value)


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
    email: str
    message: str = Field(min_length=1, max_length=2000)
    enquiry_type: EnquiryType = EnquiryType.GENERAL
    website: str | None = Field(default=None, max_length=200)

    @field_validator('name', mode='before')
    @classmethod
    def require_name(cls, value: object) -> str:
        return validate_required_text(value, field_name='Name', max_length=120)

    @field_validator('phone', mode='before')
    @classmethod
    def require_phone(cls, value: object) -> str:
        phone = validate_phone(value, required=True)
        if not phone:
            raise ValueError('Phone is required')
        return phone

    @field_validator('email', mode='before')
    @classmethod
    def require_email(cls, value: object) -> str:
        email = validate_email(value, required=True)
        if not email:
            raise ValueError('Email is required')
        return email

    @field_validator('message', mode='before')
    @classmethod
    def require_message(cls, value: object) -> str:
        return validate_required_text(value, field_name='Message', max_length=2000)

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
