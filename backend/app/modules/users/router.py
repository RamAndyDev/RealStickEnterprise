from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.roles import UserRole
from app.core.security import CurrentProfile, require_role
from app.modules.users.schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeePasswordResetRequest,
    EmployeeUpdate,
    ManagedUser,
    PasswordResetResponse,
    UserCreateResponse,
    UserListResponse,
)
from app.modules.users.service import UsersService

admin_router = APIRouter(prefix='/admin', tags=['admin-users'])
owner_router = APIRouter(prefix='/owner', tags=['owner-employees'])

SystemAdmin = Annotated[CurrentProfile, Depends(require_role(UserRole.SYSTEM_ADMIN))]
FranchiseOwner = Annotated[CurrentProfile, Depends(require_role(UserRole.FRANCHISE_OWNER))]


def get_users_service() -> UsersService:
    return UsersService()


@admin_router.get('/users', response_model=UserListResponse)
def list_users(
    _: SystemAdmin,
    role: UserRole | None = Query(default=None),
    franchise_id: UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    service: UsersService = Depends(get_users_service),
) -> UserListResponse:
    return service.list_users(
        role=role,
        franchise_id=franchise_id,
        is_active=is_active,
        search=search,
    )


@admin_router.post('/users', response_model=UserCreateResponse, status_code=201)
def create_user(
    body: AdminUserCreate,
    profile: SystemAdmin,
    service: UsersService = Depends(get_users_service),
) -> UserCreateResponse:
    return service.create_user(body, profile)


@admin_router.get('/users/{user_id}', response_model=ManagedUser)
def get_user(
    user_id: UUID,
    _: SystemAdmin,
    service: UsersService = Depends(get_users_service),
) -> ManagedUser:
    return service.get_user(user_id)


@admin_router.patch('/users/{user_id}', response_model=ManagedUser)
def update_user(
    user_id: UUID,
    body: AdminUserUpdate,
    profile: SystemAdmin,
    service: UsersService = Depends(get_users_service),
) -> ManagedUser:
    return service.update_user(user_id, body, profile)


@admin_router.post('/users/{user_id}/reset-password', response_model=PasswordResetResponse)
def reset_user_password(
    user_id: UUID,
    _: SystemAdmin,
    service: UsersService = Depends(get_users_service),
) -> PasswordResetResponse:
    return service.reset_password(user_id)


@owner_router.get('/employees', response_model=EmployeeListResponse)
def list_employees(
    profile: FranchiseOwner,
    service: UsersService = Depends(get_users_service),
) -> EmployeeListResponse:
    return service.list_employees(profile)


@owner_router.post('/employees', response_model=UserCreateResponse, status_code=201)
def create_employee(
    body: EmployeeCreate,
    profile: FranchiseOwner,
    service: UsersService = Depends(get_users_service),
) -> UserCreateResponse:
    return service.create_employee(profile, body)


@owner_router.get('/employees/{employee_id}', response_model=ManagedUser)
def get_employee(
    employee_id: UUID,
    profile: FranchiseOwner,
    service: UsersService = Depends(get_users_service),
) -> ManagedUser:
    return service.get_employee(profile, employee_id)


@owner_router.patch('/employees/{employee_id}', response_model=ManagedUser)
def update_employee(
    employee_id: UUID,
    body: EmployeeUpdate,
    profile: FranchiseOwner,
    service: UsersService = Depends(get_users_service),
) -> ManagedUser:
    return service.update_employee(profile, employee_id, body)


@owner_router.post('/employees/{employee_id}/reset-password', response_model=PasswordResetResponse)
def reset_employee_password(
    employee_id: UUID,
    body: EmployeePasswordResetRequest,
    profile: FranchiseOwner,
    service: UsersService = Depends(get_users_service),
) -> PasswordResetResponse:
    return service.reset_employee_password(profile, employee_id, body)
