from fastapi import APIRouter, Depends
from uuid import UUID

from app.core.roles import UserRole
from app.core.security import (
    CurrentProfile,
    get_current_profile,
    require_franchise_access,
    require_role,
)
from app.modules.auth.schemas import (
    AuthTestResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    MeResponse,
)
from app.modules.users.service import UsersService

router = APIRouter(prefix='/auth', tags=['auth'])


def get_users_service() -> UsersService:
    return UsersService()


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
        full_name=profile.full_name,
        role=profile.role,
        franchise_id=profile.franchise_id,
        franchise_name=franchise_name,
        phone=profile.phone,
        is_active=profile.is_active,
        created_at=profile.created_at,
    )


@router.post('/change-password', response_model=ChangePasswordResponse)
def change_password(
    body: ChangePasswordRequest,
    profile: CurrentProfile = Depends(get_current_profile),
    service: UsersService = Depends(get_users_service),
) -> ChangePasswordResponse:
    """Change the authenticated user's own password. Never accepts a target user id."""
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
