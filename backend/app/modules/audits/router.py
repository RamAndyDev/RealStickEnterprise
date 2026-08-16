from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.roles import UserRole
from app.core.security import CurrentProfile, require_role
from app.modules.audits.schemas import (
    AuditCreate,
    AuditDetail,
    AuditListResponse,
    FranchiseAuditStatus,
)
from app.modules.audits.service import AuditsService

router = APIRouter(prefix='/audits', tags=['audits'])

AuditUser = Annotated[
    CurrentProfile,
    Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.FRANCHISE_OWNER)),
]


def get_audits_service() -> AuditsService:
    return AuditsService()


@router.get('', response_model=AuditListResponse)
def list_audits(
    profile: AuditUser,
    franchise_id: UUID | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    overall_status: FranchiseAuditStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: AuditsService = Depends(get_audits_service),
) -> AuditListResponse:
    return service.list_audits(
        profile,
        franchise_id=franchise_id,
        from_date=from_date,
        to_date=to_date,
        overall_status=overall_status,
        page=page,
        page_size=page_size,
    )


@router.post('', response_model=AuditDetail, status_code=201)
def create_audit(
    body: AuditCreate,
    profile: AuditUser,
    service: AuditsService = Depends(get_audits_service),
) -> AuditDetail:
    return service.create_audit(profile, body)


@router.get('/{audit_id}', response_model=AuditDetail)
def get_audit(
    audit_id: UUID,
    profile: AuditUser,
    service: AuditsService = Depends(get_audits_service),
) -> AuditDetail:
    return service.get_audit(profile, audit_id)
