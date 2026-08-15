from __future__ import annotations

from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError

from app.core.config import get_settings
from app.db.supabase import get_supabase

PROFILE_COLUMNS = (
    'id, full_name, role, franchise_id, phone, is_active, created_at, updated_at'
)


class UsersRepository:
    def __init__(self) -> None:
        self._db = get_supabase()

    def list_profiles(
        self,
        *,
        role: str | None = None,
        roles: list[str] | None = None,
        franchise_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> list[dict[str, Any]]:
        query = self._db.table('profiles').select(PROFILE_COLUMNS)
        if role:
            query = query.eq('role', role)
        elif roles:
            query = query.in_('role', roles)
        if franchise_id is not None:
            query = query.eq('franchise_id', str(franchise_id))
        if is_active is not None:
            query = query.eq('is_active', is_active)
        response = query.order('created_at', desc=True).execute()
        return list(response.data or [])

    def get_profile(self, profile_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('profiles')
            .select(PROFILE_COLUMNS)
            .eq('id', str(profile_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def create_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._db.table('profiles').insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError('Profile insert returned no data')
        return rows[0]

    def update_profile(self, profile_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._db.table('profiles')
            .update(payload)
            .eq('id', str(profile_id))
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError('Profile update returned no data')
        return rows[0]

    def count_active_employees(
        self,
        franchise_id: UUID,
        *,
        exclude_id: UUID | None = None,
    ) -> int:
        response = (
            self._db.table('profiles')
            .select('id')
            .eq('franchise_id', str(franchise_id))
            .eq('role', 'EMPLOYEE')
            .eq('is_active', True)
            .execute()
        )
        rows = list(response.data or [])
        if exclude_id is not None:
            rows = [row for row in rows if str(row.get('id')) != str(exclude_id)]
        return len(rows)

    def count_active_admins(self, *, exclude_id: UUID | None = None) -> int:
        response = (
            self._db.table('profiles')
            .select('id')
            .eq('role', 'SYSTEM_ADMIN')
            .eq('is_active', True)
            .execute()
        )
        rows = list(response.data or [])
        if exclude_id is not None:
            rows = [row for row in rows if str(row.get('id')) != str(exclude_id)]
        return len(rows)

    def get_franchise(self, franchise_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('franchises')
            .select('id, name, employee_limit, owner_email')
            .eq('id', str(franchise_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def update_franchise_owner_email(self, franchise_id: UUID, owner_email: str) -> None:
        self._db.table('franchises').update({'owner_email': owner_email}).eq(
            'id', str(franchise_id)
        ).execute()

    def franchise_name_map(self, franchise_ids: list[str]) -> dict[str, str]:
        unique_ids = [fid for fid in dict.fromkeys(franchise_ids) if fid]
        if not unique_ids:
            return {}
        response = (
            self._db.table('franchises')
            .select('id, name')
            .in_('id', unique_ids)
            .execute()
        )
        return {str(row['id']): row.get('name') or '' for row in (response.data or [])}

    def list_auth_emails(self) -> dict[str, str | None]:
        emails: dict[str, str | None] = {}
        try:
            page = 1
            per_page = 200
            while page <= 20:
                result = self._db.auth.admin.list_users(page=page, per_page=per_page)
                users = getattr(result, 'users', None) or []
                for user in users:
                    user_id = str(getattr(user, 'id'))
                    raw_email = getattr(user, 'email', None)
                    emails[user_id] = str(raw_email).strip().lower() if raw_email else None
                if len(users) < per_page:
                    break
                page += 1
        except TypeError:
            result = self._db.auth.admin.list_users()
            users = getattr(result, 'users', None) or []
            for user in users:
                user_id = str(getattr(user, 'id'))
                raw_email = getattr(user, 'email', None)
                emails[user_id] = str(raw_email).strip().lower() if raw_email else None
        return emails

    def get_auth_email(self, user_id: str) -> str | None:
        try:
            result = self._db.auth.admin.get_user_by_id(user_id)
        except Exception:
            return self.list_auth_emails().get(user_id)
        user = getattr(result, 'user', result)
        raw_email = getattr(user, 'email', None)
        return str(raw_email).strip().lower() if raw_email else None

    def find_auth_user_id_by_email(self, email: str) -> str | None:
        normalized = email.strip().lower()
        emails = self.list_auth_emails()
        for user_id, user_email in emails.items():
            if user_email == normalized:
                return user_id
        return None

    def invite_auth_user(self, *, email: str, full_name: str, redirect_to: str) -> Any:
        return self._db.auth.admin.invite_user_by_email(
            email,
            {
                'data': {'full_name': full_name},
                'redirect_to': redirect_to,
            },
        )

    def create_auth_user_with_temp_password(
        self,
        *,
        email: str,
        full_name: str,
        password: str,
    ) -> Any:
        return self._db.auth.admin.create_user(
            {
                'email': email,
                'password': password,
                'email_confirm': True,
                'user_metadata': {'full_name': full_name},
            }
        )

    def send_recovery_email(self, *, email: str, redirect_to: str) -> Any:
        """Send the Supabase Auth recovery email (POST /recover). Does not log links."""
        return self._db.auth.reset_password_for_email(email, {'redirect_to': redirect_to})

    def update_auth_password(self, user_id: str, password: str) -> None:
        self._db.auth.admin.update_user_by_id(user_id, {'password': password})

    def delete_auth_user(self, user_id: str) -> None:
        self._db.auth.admin.delete_user(user_id)

    def password_reset_redirect_url(self) -> str:
        return get_settings().password_reset_redirect_url

    @staticmethod
    def is_unique_violation(exc: Exception) -> bool:
        if isinstance(exc, APIError):
            code = getattr(exc, 'code', None) or ''
            message = str(exc)
            return code == '23505' or 'duplicate' in message.lower() or 'unique' in message.lower()
        message = str(exc).lower()
        return 'duplicate' in message or 'unique' in message

    @staticmethod
    def is_employee_limit_violation(exc: Exception) -> bool:
        message = str(exc).lower()
        if isinstance(exc, APIError):
            message = f'{getattr(exc, "message", "")} {exc}'.lower()
        return 'maximum of' in message and 'active employees' in message
