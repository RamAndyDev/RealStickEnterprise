from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.db.supabase import get_supabase

SESSION_COLUMNS = (
    'id, employee_id, employee_name_snapshot, auth_session_id, '
    'login_at, logout_at, status, created_at, updated_at'
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class EmployeeSessionsRepository:
    def __init__(self) -> None:
        self._db = get_supabase()

    def insert(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._db.table('employee_sessions').insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError('Employee session insert returned no data')
        return rows[0]

    def get_active_by_auth_session_id(self, auth_session_id: str) -> dict[str, Any] | None:
        response = (
            self._db.table('employee_sessions')
            .select(SESSION_COLUMNS)
            .eq('auth_session_id', auth_session_id)
            .eq('status', 'ACTIVE')
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def get_active_by_id(self, session_id: UUID, employee_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('employee_sessions')
            .select(SESSION_COLUMNS)
            .eq('id', str(session_id))
            .eq('employee_id', str(employee_id))
            .eq('status', 'ACTIVE')
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def get_active_for_employee_auth_session(
        self,
        employee_id: UUID,
        auth_session_id: str,
    ) -> dict[str, Any] | None:
        response = (
            self._db.table('employee_sessions')
            .select(SESSION_COLUMNS)
            .eq('employee_id', str(employee_id))
            .eq('auth_session_id', auth_session_id)
            .eq('status', 'ACTIVE')
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def complete(self, session_id: UUID, *, logout_at: str | None = None) -> dict[str, Any]:
        response = (
            self._db.table('employee_sessions')
            .update(
                {
                    'logout_at': logout_at or _utcnow(),
                    'status': 'COMPLETED',
                }
            )
            .eq('id', str(session_id))
            .eq('status', 'ACTIVE')
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError('Employee session complete returned no data')
        return rows[0]

    def list_by_employee(self, employee_id: UUID, *, limit: int = 10) -> list[dict[str, Any]]:
        response = (
            self._db.table('employee_sessions')
            .select(SESSION_COLUMNS)
            .eq('employee_id', str(employee_id))
            .order('login_at', desc=True)
            .limit(limit)
            .execute()
        )
        return list(response.data or [])

    def list_active(self) -> list[dict[str, Any]]:
        response = (
            self._db.table('employee_sessions')
            .select('employee_id')
            .eq('status', 'ACTIVE')
            .execute()
        )
        return list(response.data or [])
