from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.roles import UserRole
from app.core.security import CurrentProfile, require_role
from app.modules.franchises.schemas import (
    ApplicationListResponse,
    FranchiseApplicationSummary,
    FranchiseCreate,
    FranchiseDetail,
    FranchiseListResponse,
    FranchiseOwnerAssign,
    FranchiseOwnerCreate,
    FranchiseOwnerCreateResponse,
    FranchiseStatus,
    FranchiseStatusUpdate,
    FranchiseOfflinePaymentCreate,
    FranchiseUpdate,
    LaunchChecklistItem,
    LaunchChecklistItemUpdate,
)
from app.modules.franchises.service import FranchiseService

router = APIRouter(prefix='/admin', tags=['admin-franchises'])

SystemAdmin = Annotated[CurrentProfile, Depends(require_role(UserRole.SYSTEM_ADMIN))]


def get_franchise_service() -> FranchiseService:
    return FranchiseService()


@router.get('/franchises', response_model=FranchiseListResponse)
def list_franchises(
    _: SystemAdmin,
    status: FranchiseStatus | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    include_archived: bool = Query(default=False),
    service: FranchiseService = Depends(get_franchise_service),
) -> FranchiseListResponse:
    return service.list_franchises(
        status=status,
        search=search,
        include_archived=include_archived,
    )


@router.get('/franchises/{franchise_id}', response_model=FranchiseDetail)
def get_franchise(
    franchise_id: UUID,
    _: SystemAdmin,
    service: FranchiseService = Depends(get_franchise_service),
) -> FranchiseDetail:
    return service.get_franchise(franchise_id)


@router.post('/franchises', response_model=FranchiseDetail, status_code=201)
def create_franchise(
    body: FranchiseCreate,
    profile: SystemAdmin,
    service: FranchiseService = Depends(get_franchise_service),
) -> FranchiseDetail:
    return service.create_franchise(body, actor=profile)


@router.patch('/franchises/{franchise_id}', response_model=FranchiseDetail)
def update_franchise(
    franchise_id: UUID,
    body: FranchiseUpdate,
    _: SystemAdmin,
    service: FranchiseService = Depends(get_franchise_service),
) -> FranchiseDetail:
    return service.update_franchise(franchise_id, body)


@router.patch('/franchises/{franchise_id}/status', response_model=FranchiseDetail)
def update_franchise_status(
    franchise_id: UUID,
    body: FranchiseStatusUpdate,
    _: SystemAdmin,
    service: FranchiseService = Depends(get_franchise_service),
) -> FranchiseDetail:
    return service.update_status(franchise_id, body)


@router.patch('/franchises/{franchise_id}/owner', response_model=FranchiseDetail)
def assign_franchise_owner(
    franchise_id: UUID,
    body: FranchiseOwnerAssign,
    profile: SystemAdmin,
    service: FranchiseService = Depends(get_franchise_service),
) -> FranchiseDetail:
    return service.assign_owner(franchise_id, body, profile)


@router.post(
    '/franchises/{franchise_id}/owners',
    response_model=FranchiseOwnerCreateResponse,
    status_code=201,
)
def create_franchise_owner(
    franchise_id: UUID,
    body: FranchiseOwnerCreate,
    profile: SystemAdmin,
    service: FranchiseService = Depends(get_franchise_service),
) -> FranchiseOwnerCreateResponse:
    return service.create_owner(franchise_id, body, profile)


@router.post(
    '/franchises/{franchise_id}/payments',
    response_model=FranchiseDetail,
    status_code=201,
)
def record_offline_franchise_payment(
    franchise_id: UUID,
    body: FranchiseOfflinePaymentCreate,
    _: SystemAdmin,
    service: FranchiseService = Depends(get_franchise_service),
) -> FranchiseDetail:
    return service.record_offline_payment(franchise_id, body)


@router.get('/franchises/{franchise_id}/launch-checklist', response_model=list[LaunchChecklistItem])
def get_launch_checklist(
    franchise_id: UUID,
    _: SystemAdmin,
    service: FranchiseService = Depends(get_franchise_service),
) -> list[LaunchChecklistItem]:
    return service.get_launch_progress(franchise_id)


@router.patch(
    '/franchises/{franchise_id}/launch-checklist/{item_id}',
    response_model=LaunchChecklistItem,
)
def update_launch_checklist_item(
    franchise_id: UUID,
    item_id: UUID,
    body: LaunchChecklistItemUpdate,
    profile: SystemAdmin,
    service: FranchiseService = Depends(get_franchise_service),
) -> LaunchChecklistItem:
    return service.update_launch_item(franchise_id, item_id, body, profile)


@router.get('/franchise-applications', response_model=ApplicationListResponse)
def list_franchise_applications(
    _: SystemAdmin,
    status: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    service: FranchiseService = Depends(get_franchise_service),
) -> ApplicationListResponse:
    items = service.list_applications(status=status, search=search)
    return ApplicationListResponse(items=items, total=len(items))


@router.get('/franchise-applications/{application_id}', response_model=FranchiseApplicationSummary)
def get_franchise_application(
    application_id: UUID,
    _: SystemAdmin,
    service: FranchiseService = Depends(get_franchise_service),
) -> FranchiseApplicationSummary:
    return service.get_application(application_id)
