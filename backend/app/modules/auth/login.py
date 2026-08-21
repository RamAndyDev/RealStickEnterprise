"""Resolve Email/User ID and authenticate through Supabase Auth."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.roles import UserRole
from app.modules.auth.identity import (
    INVALID_CREDENTIALS,
    is_internal_employee_identity,
    looks_like_email,
    normalize_login_id,
)
from app.modules.employee_sessions.service import EmployeeSessionsService
from app.modules.users.repository import UsersRepository

logger = logging.getLogger(__name__)


class AuthLoginService:
    def __init__(
        self,
        repo: UsersRepository | None = None,
        sessions: EmployeeSessionsService | None = None,
    ) -> None:
        self.repo = repo or UsersRepository()
        self.sessions = sessions or EmployeeSessionsService()

    def login(self, identifier: str, password: str) -> dict[str, Any]:
        raw = identifier.strip()
        if not raw or not password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)

        if looks_like_email(raw):
            email = raw.lower()
            if is_internal_employee_identity(email):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=INVALID_CREDENTIALS,
                )
            profile = self.repo.get_profile_by_auth_email(email)
            if profile and profile.get('role') == UserRole.EMPLOYEE.value:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=INVALID_CREDENTIALS,
                )
            if profile and not profile.get('is_active', False):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=INVALID_CREDENTIALS,
                )
            return self._sign_in(email, password)

        login_id = normalize_login_id(raw)
        profile = self.repo.get_profile_by_login_id(login_id)
        if (
            not profile
            or profile.get('role') != UserRole.EMPLOYEE.value
            or not profile.get('is_active', False)
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)

        auth_email = self.repo.get_auth_email(str(profile['id']))
        if not auth_email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
        tokens = self._sign_in(auth_email, password)
        self._track_employee_login(profile, tokens)
        return tokens

    def _sign_in(self, email: str, password: str) -> dict[str, Any]:
        try:
            payload = self.repo.sign_in_with_password(email, password)
        except HTTPException:
            raise
        except Exception:
            logger.warning('Password sign-in failed')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=INVALID_CREDENTIALS,
            ) from None

        access = payload.get('access_token')
        refresh = payload.get('refresh_token')
        if not access or not refresh:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
        return {
            'access_token': access,
            'refresh_token': refresh,
            'token_type': payload.get('token_type') or 'bearer',
            'expires_in': payload.get('expires_in'),
        }

    def _track_employee_login(self, profile: dict[str, Any], tokens: dict[str, Any]) -> None:
        """Record an ACTIVE employee session. Tracking failure must not block login."""
        try:
            row = self.sessions.record_login(
                employee_id=profile['id'],
                employee_name=str(profile.get('full_name') or 'Employee'),
                access_token=tokens.get('access_token'),
                role=str(profile.get('role') or ''),
            )
        except Exception:
            logger.warning('Employee session tracking failed after login', exc_info=True)
            return
        if row and row.get('id'):
            tokens['employee_session_id'] = row['id']


def supabase_password_grant(email: str, password: str) -> dict[str, Any]:
    """Call GoTrue password grant. Never log the password or API key."""
    settings = get_settings()
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password"
    api_key = settings.supabase_service_role_key
    try:
        response = httpx.post(
            url,
            headers={
                'apikey': api_key,
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={'email': email, 'password': password},
            timeout=15.0,
        )
    except httpx.HTTPError as exc:
        logger.warning('Auth token request failed')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Unable to sign in right now',
        ) from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
    data = response.json()
    if not isinstance(data, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
    return data
