from __future__ import annotations

from datetime import datetime
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GalleryMediaType = Literal['IMAGE', 'VIDEO', 'TESTIMONIAL']

_BLOCKED_URL_SCHEMES = {'javascript', 'data', 'file', 'vbscript'}


def _strip_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError('value must be a string')
    stripped = value.strip()
    return stripped or None


def validate_external_video_url(value: str) -> str:
    parsed = urlparse(value.strip())
    scheme = (parsed.scheme or '').lower()
    if scheme != 'https':
        raise ValueError('Video URL must use HTTPS')
    if scheme in _BLOCKED_URL_SCHEMES:
        raise ValueError('Video URL is not allowed')
    host = (parsed.hostname or '').lower()
    if not host or host in {'localhost', '127.0.0.1', '::1'}:
        raise ValueError('Video URL host is not allowed')
    if '.' not in host:
        raise ValueError('Video URL host is not allowed')
    return value.strip()


class AdminGalleryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id: UUID
    title: str | None = None
    caption: str | None = None
    author_name: str | None = None
    media_type: GalleryMediaType
    media_url: str | None = None
    display_order: int
    is_approved: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class AdminGalleryListResponse(BaseModel):
    items: list[AdminGalleryItem]
    total: int


class GalleryCreate(BaseModel):
    media_type: GalleryMediaType
    title: str | None = Field(default=None, max_length=160)
    caption: str | None = Field(default=None, max_length=2000)
    author_name: str | None = Field(default=None, max_length=120)
    media_url: str | None = Field(default=None, max_length=2000)
    display_order: int = Field(default=0, ge=0)
    is_approved: bool = False

    @field_validator('title', 'caption', 'author_name', mode='before')
    @classmethod
    def strip_optional(cls, value: object) -> str | None:
        return _strip_text(value)

    @field_validator('media_url', mode='before')
    @classmethod
    def strip_url(cls, value: object) -> str | None:
        return _strip_text(value)

    @model_validator(mode='after')
    def validate_by_type(self) -> 'GalleryCreate':
        if self.media_type == 'VIDEO':
            if not self.media_url:
                raise ValueError('Video URL is required')
            self.media_url = validate_external_video_url(self.media_url)
        elif self.media_type == 'TESTIMONIAL':
            if not self.caption:
                raise ValueError('Testimonial quote is required')
            if not self.author_name:
                raise ValueError('Testimonial author is required')
            self.media_url = None
        else:
            self.media_url = None
        return self


class GalleryUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    caption: str | None = Field(default=None, max_length=2000)
    author_name: str | None = Field(default=None, max_length=120)
    media_url: str | None = Field(default=None, max_length=2000)
    display_order: int | None = Field(default=None, ge=0)
    is_approved: bool | None = None
    is_archived: bool | None = None

    @field_validator('title', 'caption', 'author_name', mode='before')
    @classmethod
    def strip_optional(cls, value: object) -> str | None:
        if value is None:
            return None
        return _strip_text(value)

    @field_validator('media_url', mode='before')
    @classmethod
    def strip_url(cls, value: object) -> str | None:
        if value is None:
            return None
        return _strip_text(value)


class PublicGalleryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id: UUID
    title: str | None = None
    caption: str | None = None
    author_name: str | None = None
    media_type: GalleryMediaType
    media_url: str | None = None
    display_order: int


class PublicGalleryListResponse(BaseModel):
    items: list[PublicGalleryItem]
    total: int
