from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException, status

from app.core.roles import UserRole
from app.core.security import AuthenticatedUser, CurrentProfile
from app.modules.employee_sessions.repository import EmployeeSessionsRepository
from app.modules.employee_sessions.schemas import (
    EmployeeSessionItem,
    EmployeeSessionListResponse,
)
from app.modules.users.repository import UsersRepository

logger = logging.getLogger(__name__)

DEFAULT_SESSION_HISTORY_LIMIT = 10
_UNVERIFIED_JWT_ALGORITHMS = ('ES256', 'RS256', 'HS256')


def extract_auth_session_id(access_token: str | None) -> str:
    """Best-effort identifier for this login. Prefers JWT session_id when present."""
    if not access_token or not access_token.strip():
        return str(uuid4())
    try:
        payload = jwt.decode(
            access_token,
            options={
                'verify_signature': False,
                'verify_aud': False,
                'verify_exp': False,
                'verify_iss': False,
            },
            algorithms=list(_UNVERIFIED_JWT_ALGORITHMS),
        )
    except jwt.PyJWTError:
        return str(uuid4())
    raw = payload.get('session_id') if isinstance(payload, dict) else None
    if raw is None:
        return str(uuid4())
    session_id = str(raw).strip()
    return session_id or str(uuid4())


class EmployeeSessionsService:
    def __init__(
        self,
        repo: EmployeeSessionsRepository | None = None,
        users_repo: UsersRepository | None = None,
    ) -> None:
        self.repo = repo or EmployeeSessionsRepository()
        self.users_repo = users_repo or UsersRepository()

    def record_login(
        self,
        *,
        employee_id: UUID | str,
        employee_name: str,
        access_token: str | None,
        role: str | None,
    ) -> dict[str, Any] | None:
        if role != UserRole.EMPLOYEE.value:
            return None
        name = (employee_name or '').strip() or 'Employee'
        auth_session_id = extract_auth_session_id(access_token)
        existing = self.repo.get_active_by_auth_session_id(auth_session_id)
        if existing and str(existing.get('employee_id')) == str(employee_id):
            return existing
        return self.repo.insert(
            {
                'employee_id': str(employee_id),
                'employee_name_snapshot': name,
                'auth_session_id': auth_session_id,
                'login_at': datetime.now(timezone.utc).isoformat(),
                'status': 'ACTIVE',
                'logout_at': None,
            }
        )

    def complete_logout(
        self,
        *,
        profile: CurrentProfile,
        auth_user: AuthenticatedUser,
        employee_session_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        if profile.role != UserRole.EMPLOYEE:
            return None

        row = None
        auth_session_id = (auth_user.session_id or '').strip()
        if auth_session_id:
            row = self.repo.get_active_for_employee_auth_session(profile.id, auth_session_id)
        if row is None and employee_session_id is not None:
            row = self.repo.get_active_by_id(employee_session_id, profile.id)
        if row is None:
            return None
        return self.repo.complete(UUID(str(row['id'])))

    def logged_in_employee_ids(self) -> set[str]:
        """Return employee ids with an ACTIVE session. Failures must not break listing."""
        try:
            return {
                str(item.get('employee_id'))
                for item in self.repo.list_active()
                if item.get('employee_id')
            }
        except Exception:
            logger.warning('Unable to load active employee sessions', exc_info=True)
            return set()

    def list_owner_employee_sessions(
        self,
        owner: CurrentProfile,
        employee_id: UUID,
        *,
        limit: int = DEFAULT_SESSION_HISTORY_LIMIT,
    ) -> EmployeeSessionListResponse:
        if owner.franchise_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Franchise owner profile must belong to a franchise',
            )
        profile = self.users_repo.get_profile(employee_id)
        if not profile or profile.get('role') != UserRole.EMPLOYEE.value:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Employee not found')
        if str(profile.get('franchise_id')) != str(owner.franchise_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Access to this employee is not allowed',
            )
        rows = self.repo.list_by_employee(employee_id, limit=limit)
        return EmployeeSessionListResponse(
            employee_id=employee_id,
            employee_name=str(profile.get('full_name') or 'Employee'),
            login_id=profile.get('login_id'),
            items=[self._to_item(row) for row in rows],
        )

    def _to_item(self, row: dict[str, Any]) -> EmployeeSessionItem:
        return EmployeeSessionItem(
            id=row['id'],
            employee_id=row['employee_id'],
            employee_name_snapshot=row.get('employee_name_snapshot') or 'Employee',
            login_at=row['login_at'],
            logout_at=row.get('logout_at'),
            status=row.get('status') or 'ACTIVE',
            created_at=row.get('created_at'),
        )
