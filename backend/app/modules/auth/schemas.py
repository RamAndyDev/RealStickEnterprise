from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.roles import UserRole


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None = None
    login_id: str | None = None
    full_name: str
    role: UserRole
    franchise_id: UUID | None = None
    franchise_name: str | None = None
    phone: str | None = None
    is_active: bool
    created_at: datetime | None = None


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=128)

    @field_validator('identifier', 'password')
    @classmethod
    def strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError('This field is required')
        return stripped


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int | None = None
    employee_session_id: UUID | None = None


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def require_password(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 8:
            raise ValueError('Password must be at least 8 characters')
        return stripped


class ChangePasswordResponse(BaseModel):
    message: str


class AuthTestResponse(BaseModel):
    """TEMPORARY DEV RESPONSE — remove with /auth/test/* endpoints."""

    status: str = 'ok'
    endpoint: str
    message: str = 'TEMPORARY DEV ENDPOINT — remove after auth verification'
    role: UserRole
    franchise_id: UUID | None = None
