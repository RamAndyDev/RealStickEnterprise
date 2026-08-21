from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.roles import UserRole
from app.core.security import CurrentProfile, require_role
from app.modules.employee_sessions.schemas import EmployeeSessionListResponse
from app.modules.employee_sessions.service import (
    DEFAULT_SESSION_HISTORY_LIMIT,
    EmployeeSessionsService,
)

owner_router = APIRouter(prefix='/owner/employees', tags=['owner-employee-sessions'])

FranchiseOwner = Annotated[CurrentProfile, Depends(require_role(UserRole.FRANCHISE_OWNER))]


def get_employee_sessions_service() -> EmployeeSessionsService:
    return EmployeeSessionsService()


@owner_router.get('/{employee_id}/sessions', response_model=EmployeeSessionListResponse)
def list_employee_sessions(
    employee_id: UUID,
    profile: FranchiseOwner,
    limit: int = Query(default=DEFAULT_SESSION_HISTORY_LIMIT, ge=1, le=50),
    service: EmployeeSessionsService = Depends(get_employee_sessions_service),
) -> EmployeeSessionListResponse:
    return service.list_owner_employee_sessions(profile, employee_id, limit=limit)
