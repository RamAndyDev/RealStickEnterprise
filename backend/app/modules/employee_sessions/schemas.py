from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

EmployeeSessionStatus = Literal['ACTIVE', 'COMPLETED']


class EmployeeSessionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    employee_name_snapshot: str
    login_at: datetime
    logout_at: datetime | None = None
    status: EmployeeSessionStatus
    created_at: datetime | None = None


class EmployeeSessionListResponse(BaseModel):
    employee_id: UUID
    employee_name: str
    login_id: str | None = None
    items: list[EmployeeSessionItem]


class EmployeeSessionLogoutRequest(BaseModel):
    employee_session_id: UUID | None = None


class EmployeeSessionLogoutResponse(BaseModel):
    ok: bool = True
