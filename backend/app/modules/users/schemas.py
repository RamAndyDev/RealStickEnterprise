from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.roles import UserRole
from app.modules.auth.identity import validate_login_id

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _normalize_email(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError('email must be a string')
    stripped = value.strip().lower()
    if not stripped:
        return None
    if not _EMAIL_RE.match(stripped):
        raise ValueError('Invalid email format')
    return stripped


def _strip_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError('value must be a string')
    stripped = value.strip()
    return stripped or None


class ManagedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str | None = None
    login_id: str | None = None
    phone: str | None = None
    role: UserRole
    franchise_id: UUID | None = None
    franchise_name: str | None = None
    is_active: bool
    is_logged_in: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserListResponse(BaseModel):
    items: list[ManagedUser]
    total: int


class EmployeeListResponse(UserListResponse):
    active_count: int
    employee_limit: int


class AdminUserCreate(BaseModel):
    """SYSTEM_ADMIN creates a user. franchise_id is required except for SYSTEM_ADMIN."""

    full_name: str = Field(min_length=1, max_length=200)
    email: str
    phone: str | None = Field(default=None, max_length=40)
    role: UserRole
    franchise_id: UUID | None = None

    @field_validator('full_name', mode='before')
    @classmethod
    def require_name(cls, value: object) -> str:
        stripped = _strip_text(value)
        if not stripped:
            raise ValueError('Name is required')
        return stripped

    @field_validator('email', mode='before')
    @classmethod
    def require_email(cls, value: object) -> str:
        normalized = _normalize_email(value)
        if not normalized:
            raise ValueError('Email is required')
        return normalized

    @field_validator('phone', mode='before')
    @classmethod
    def strip_phone(cls, value: object) -> str | None:
        return _strip_text(value)

    @model_validator(mode='after')
    def validate_role_franchise(self) -> AdminUserCreate:
        if self.role == UserRole.EMPLOYEE:
            raise ValueError('Employees are managed by franchise owners')
        if self.role == UserRole.SYSTEM_ADMIN:
            if self.franchise_id is not None:
                raise ValueError('SYSTEM_ADMIN cannot be assigned to a franchise')
        elif self.franchise_id is None:
            raise ValueError(f'{self.role.value} must belong to a franchise')
        return self


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None
    franchise_id: UUID | None = None

    @field_validator('full_name', mode='before')
    @classmethod
    def strip_name(cls, value: object) -> str | None:
        if value is None:
            return None
        stripped = _strip_text(value)
        if not stripped:
            raise ValueError('Name cannot be empty')
        return stripped

    @field_validator('phone', mode='before')
    @classmethod
    def strip_phone(cls, value: object) -> str | None:
        return _strip_text(value)


class EmployeeCreate(BaseModel):
    """Owner creates an employee. franchise_id is never taken from the client."""

    model_config = ConfigDict(extra='ignore')

    full_name: str = Field(min_length=1, max_length=200)
    login_id: str
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=40)

    @field_validator('full_name', mode='before')
    @classmethod
    def require_name(cls, value: object) -> str:
        stripped = _strip_text(value)
        if not stripped:
            raise ValueError('Employee name is required')
        return stripped

    @field_validator('login_id', mode='before')
    @classmethod
    def require_login_id(cls, value: object) -> str:
        return validate_login_id(value)

    @field_validator('password')
    @classmethod
    def require_password(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 8:
            raise ValueError('Password must be at least 8 characters')
        return stripped

    @field_validator('phone', mode='before')
    @classmethod
    def strip_phone(cls, value: object) -> str | None:
        return _strip_text(value)

    @model_validator(mode='after')
    def confirm_matches(self) -> EmployeeCreate:
        if self.confirm_password is not None and self.confirm_password != self.password:
            raise ValueError('Passwords do not match')
        return self


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    login_id: str | None = None
    phone: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None

    @field_validator('full_name', mode='before')
    @classmethod
    def strip_name(cls, value: object) -> str | None:
        if value is None:
            return None
        stripped = _strip_text(value)
        if not stripped:
            raise ValueError('Employee name cannot be empty')
        return stripped

    @field_validator('phone', mode='before')
    @classmethod
    def strip_phone(cls, value: object) -> str | None:
        return _strip_text(value)

    @field_validator('login_id', mode='before')
    @classmethod
    def strip_login_id(cls, value: object) -> str:
        return validate_login_id(value)


class EmployeePasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str | None = Field(default=None, max_length=128)

    @field_validator('new_password')
    @classmethod
    def require_password(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 8:
            raise ValueError('Password must be at least 8 characters')
        return stripped

    @model_validator(mode='after')
    def confirm_matches(self) -> EmployeePasswordResetRequest:
        if self.confirm_password is not None and self.confirm_password != self.new_password:
            raise ValueError('Passwords do not match')
        return self


class UserCreateResponse(BaseModel):
    user: ManagedUser
    password_setup: str
    message: str


class PasswordResetResponse(BaseModel):
    password_setup: str
    message: str
