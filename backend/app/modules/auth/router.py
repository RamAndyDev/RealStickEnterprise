import logging
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.core.roles import UserRole
from app.core.security import (
    AuthenticatedUser,
    CurrentProfile,
    get_current_profile,
    get_current_user,
    require_franchise_access,
    require_role,
)
from app.modules.auth.login import AuthLoginService
from app.modules.auth.schemas import (
    AuthTestResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
    MeResponse,
)
from app.modules.employee_sessions.schemas import (
    EmployeeSessionLogoutRequest,
    EmployeeSessionLogoutResponse,
)
from app.modules.employee_sessions.service import EmployeeSessionsService
from app.modules.users.service import UsersService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/auth', tags=['auth'])


def get_users_service() -> UsersService:
    return UsersService()


def get_login_service() -> AuthLoginService:
    return AuthLoginService()


def get_employee_sessions_service() -> EmployeeSessionsService:
    return EmployeeSessionsService()


@router.post('/login', response_model=LoginResponse)
def login(
    body: LoginRequest,
    service: AuthLoginService = Depends(get_login_service),
) -> LoginResponse:
    """Sign in with email (admin/owner) or User ID (employee). Never returns passwords."""
    payload = service.login(body.identifier, body.password)
    return LoginResponse(
        access_token=payload['access_token'],
        refresh_token=payload['refresh_token'],
        token_type=payload.get('token_type') or 'bearer',
        expires_in=payload.get('expires_in'),
        employee_session_id=payload.get('employee_session_id'),
    )


@router.get('/me', response_model=MeResponse)
def read_me(profile: CurrentProfile = Depends(get_current_profile)) -> MeResponse:
    """Return the authenticated user's safe profile information."""
    franchise_name = None
    if profile.franchise_id is not None:
        try:
            from app.db.supabase import get_supabase

            response = (
                get_supabase()
                .table('franchises')
                .select('name')
                .eq('id', str(profile.franchise_id))
                .limit(1)
                .execute()
            )
            rows = response.data or []
            if rows:
                franchise_name = rows[0].get('name')
        except Exception:
            franchise_name = None

    return MeResponse(
        id=profile.id,
        email=profile.email,
        login_id=profile.login_id,
        full_name=profile.full_name,
        role=profile.role,
        franchise_id=profile.franchise_id,
        franchise_name=franchise_name,
        phone=profile.phone,
        is_active=profile.is_active,
        created_at=profile.created_at,
    )


@router.post('/employee-sessions/logout', response_model=EmployeeSessionLogoutResponse)
def logout_employee_session(
    profile: CurrentProfile = Depends(get_current_profile),
    user: AuthenticatedUser = Depends(get_current_user),
    body: EmployeeSessionLogoutRequest = Body(default=EmployeeSessionLogoutRequest()),
    service: EmployeeSessionsService = Depends(get_employee_sessions_service),
) -> EmployeeSessionLogoutResponse:
    """Complete the current employee session. Non-employees and missing sessions are no-ops."""
    try:
        service.complete_logout(
            profile=profile,
            auth_user=user,
            employee_session_id=body.employee_session_id,
        )
    except Exception:
        logger.warning('Employee session tracking failed on logout', exc_info=True)
    return EmployeeSessionLogoutResponse(ok=True)


@router.post('/change-password', response_model=ChangePasswordResponse)
def change_password(
    body: ChangePasswordRequest,
    profile: CurrentProfile = Depends(get_current_profile),
    service: UsersService = Depends(get_users_service),
) -> ChangePasswordResponse:
    """Admin and Owner change their own password. Employees cannot."""
    if profile.role == UserRole.EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Employees cannot change their password. Ask the franchise owner to reset it.',
        )
    service.change_own_password(profile, body.new_password)
    return ChangePasswordResponse(message='Password updated')


# ---------------------------------------------------------------------------
# TEMPORARY DEV ENDPOINTS — remove after authentication verification
# ---------------------------------------------------------------------------


@router.get(
    '/test/admin',
    response_model=AuthTestResponse,
    tags=['auth-test-temporary'],
    summary='TEMPORARY: SYSTEM_ADMIN only',
)
def test_admin_only(
    profile: CurrentProfile = Depends(require_role(UserRole.SYSTEM_ADMIN)),
) -> AuthTestResponse:
    return AuthTestResponse(
        endpoint='/auth/test/admin',
        role=profile.role,
        franchise_id=profile.franchise_id,
    )


@router.get(
    '/test/owner',
    response_model=AuthTestResponse,
    tags=['auth-test-temporary'],
    summary='TEMPORARY: FRANCHISE_OWNER only',
)
def test_owner_only(
    profile: CurrentProfile = Depends(require_role(UserRole.FRANCHISE_OWNER)),
) -> AuthTestResponse:
    return AuthTestResponse(
        endpoint='/auth/test/owner',
        role=profile.role,
        franchise_id=profile.franchise_id,
    )


@router.get(
    '/test/employee',
    response_model=AuthTestResponse,
    tags=['auth-test-temporary'],
    summary='TEMPORARY: EMPLOYEE only',
)
def test_employee_only(
    profile: CurrentProfile = Depends(require_role(UserRole.EMPLOYEE)),
) -> AuthTestResponse:
    return AuthTestResponse(
        endpoint='/auth/test/employee',
        role=profile.role,
        franchise_id=profile.franchise_id,
    )


@router.get(
    '/test/franchise/{franchise_id}',
    response_model=AuthTestResponse,
    tags=['auth-test-temporary'],
    summary='TEMPORARY: franchise-scoped access check',
)
def test_franchise_access(
    franchise_id: UUID,
    profile: CurrentProfile = Depends(require_franchise_access),
) -> AuthTestResponse:
    return AuthTestResponse(
        endpoint=f'/auth/test/franchise/{franchise_id}',
        role=profile.role,
        franchise_id=franchise_id,
    )
