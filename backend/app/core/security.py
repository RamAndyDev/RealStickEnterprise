"""Authentication and authorization dependencies for FastAPI.

Supabase Auth issues JWTs (ES256 via JWKS). FastAPI validates the JWT,
loads the application profile from public.profiles, and enforces
role/franchise rules server-side.
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.core.roles import UserRole
from app.db.supabase import get_supabase

_bearer = HTTPBearer(auto_error=False)

# Asymmetric algorithms used by Supabase JWT signing keys.
_JWKS_ALGORITHMS = ('ES256', 'RS256')
_JWKS_CACHE_LIFESPAN_SECONDS = 300.0


class AuthenticatedUser(BaseModel):
    """Identity derived from a verified Supabase access token."""

    id: UUID
    email: str | None = None
    role: str | None = None  # JWT claim (usually "authenticated"), not app role
    session_id: str | None = None  # GoTrue session_id when present; used for employee session tracking


class CurrentProfile(BaseModel):
    """Application profile loaded from public.profiles (authoritative for authz)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None = None
    login_id: str | None = None
    full_name: str
    role: UserRole
    franchise_id: UUID | None = None
    is_active: bool
    phone: str | None = None
    created_at: datetime | None = None


def _unauthorized(detail: str = 'Authentication required') -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={'WWW-Authenticate': 'Bearer'},
    )


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def get_jwks_client() -> PyJWKClient:
    """Return a process-cached PyJWKClient for the project's JWKS endpoint.

    PyJWKClient caches the JWK set (default lifespan 300s). When a JWT
    references an unknown ``kid``, ``get_signing_key`` refreshes JWKS once
    and retries — supporting key rotation without per-request fetches.
    """
    return _get_jwks_client(get_settings().supabase_jwks_url)


@lru_cache
def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(
        jwks_url,
        cache_jwk_set=True,
        lifespan=_JWKS_CACHE_LIFESPAN_SECONDS,
    )


def clear_jwks_client_cache() -> None:
    """Clear cached JWKS clients (used by tests)."""
    _get_jwks_client.cache_clear()


def decode_access_token(token: str) -> dict:
    """Validate a Supabase access token using the project JWKS (ES256/RS256)."""
    settings = get_settings()
    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=list(_JWKS_ALGORITHMS),
            audience='authenticated',
            issuer=settings.supabase_jwt_issuer,
            options={
                'require': ['exp', 'sub', 'iss', 'aud'],
            },
        )
    except PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Unable to verify authentication token',
        ) from exc
    except (PyJWKClientError, jwt.PyJWTError) as exc:
        raise _unauthorized('Invalid or expired token') from exc


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    """Extract and validate the authenticated Supabase user from the Bearer token."""
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise _unauthorized()

    token = credentials.credentials.strip()
    if not token:
        raise _unauthorized()

    payload = decode_access_token(token)
    subject = payload.get('sub')
    if not subject:
        raise _unauthorized('Token missing subject')

    try:
        user_id = UUID(str(subject))
    except ValueError as exc:
        raise _unauthorized('Token subject is invalid') from exc

    email = payload.get('email')
    raw_session_id = payload.get('session_id')
    session_id = str(raw_session_id).strip() if raw_session_id else None
    return AuthenticatedUser(
        id=user_id,
        email=str(email) if email else None,
        role=str(payload.get('role')) if payload.get('role') else None,
        session_id=session_id or None,
    )


def get_current_profile(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CurrentProfile:
    """Load the active application profile for the authenticated user."""
    try:
        response = (
            get_supabase()
            .table('profiles')
            .select('id, full_name, role, franchise_id, phone, is_active, created_at, login_id')
            .eq('id', str(user.id))
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Unable to load user profile',
        ) from exc

    rows = response.data or []
    if not rows:
        raise _forbidden('User profile not found')

    row = rows[0]
    if not row.get('is_active', False):
        raise _forbidden('User account is inactive')

    try:
        role = UserRole(row['role'])
    except ValueError as exc:
        raise _forbidden('User profile has an invalid role') from exc

    franchise_raw = row.get('franchise_id')
    franchise_id = UUID(str(franchise_raw)) if franchise_raw else None

    if role == UserRole.SYSTEM_ADMIN and franchise_id is not None:
        raise _forbidden('SYSTEM_ADMIN profile must not belong to a franchise')
    if role in {UserRole.FRANCHISE_OWNER, UserRole.EMPLOYEE} and franchise_id is None:
        raise _forbidden(f'{role.value} profile must belong to a franchise')

    from app.modules.auth.identity import is_internal_employee_identity

    email = user.email
    if role == UserRole.EMPLOYEE or is_internal_employee_identity(email):
        email = None

    return CurrentProfile(
        id=UUID(str(row['id'])),
        email=email,
        login_id=row.get('login_id'),
        full_name=row['full_name'],
        role=role,
        franchise_id=franchise_id,
        is_active=bool(row['is_active']),
        phone=row.get('phone'),
        created_at=row.get('created_at'),
    )


def require_role(*roles: UserRole):
    """Dependency factory: allow only the listed application roles."""
    allowed = frozenset(roles)

    def dependency(
        profile: Annotated[CurrentProfile, Depends(get_current_profile)],
    ) -> CurrentProfile:
        if profile.role not in allowed:
            raise _forbidden('Insufficient permissions for this resource')
        return profile

    return dependency


def enforce_franchise_access(profile: CurrentProfile, franchise_id: UUID) -> None:
    """Raise 403 unless the profile may access the given franchise."""
    if profile.role == UserRole.SYSTEM_ADMIN:
        return
    if profile.franchise_id is None or profile.franchise_id != franchise_id:
        raise _forbidden('Access to this franchise is not allowed')


def require_franchise_access(
    franchise_id: UUID,
    profile: Annotated[CurrentProfile, Depends(get_current_profile)],
) -> CurrentProfile:
    """Dependency: SYSTEM_ADMIN any franchise; others only their own."""
    enforce_franchise_access(profile, franchise_id)
    return profile
