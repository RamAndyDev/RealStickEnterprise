from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError

from app.db.supabase import get_supabase
from app.modules.franchises.schemas import FranchiseStatus

DEFAULT_LAUNCH_CHECKLIST: list[dict[str, Any]] = [
    {'item_key': 'agreement_signed', 'item_name': 'Franchise agreement signed', 'display_order': 1},
    {'item_key': 'fee_received', 'item_name': 'Franchise fee received', 'display_order': 2},
    {'item_key': 'owner_assigned', 'item_name': 'Franchise owner assigned', 'display_order': 3},
    {'item_key': 'outlet_fitted', 'item_name': 'Outlet fit-out complete', 'display_order': 4},
    {'item_key': 'staff_hired', 'item_name': 'Staff hired', 'display_order': 5},
    {'item_key': 'menu_ready', 'item_name': 'Menu & pricing ready', 'display_order': 6},
    {'item_key': 'inventory_ready', 'item_name': 'Opening inventory ready', 'display_order': 7},
    {'item_key': 'soft_launch', 'item_name': 'Soft launch complete', 'display_order': 8},
]

FRANCHISE_COLUMNS = (
    'id, name, code, owner_email, address, city, state, postal_code, tier, status, '
    'open_date, closed_at, employee_limit, settings, is_archived, created_at, updated_at'
)


class FranchiseRepository:
    def __init__(self) -> None:
        self._db = get_supabase()

    def list_franchises(
        self,
        *,
        status: FranchiseStatus | None = None,
        search: str | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        query = self._db.table('franchises').select(FRANCHISE_COLUMNS)
        if not include_archived:
            query = query.eq('is_archived', False)
        if status is not None:
            query = query.eq('status', status.value)
        response = query.order('created_at', desc=True).execute()
        rows = list(response.data or [])
        if search:
            needle = search.strip().lower()
            rows = [
                row
                for row in rows
                if needle in (row.get('name') or '').lower()
                or needle in (row.get('city') or '').lower()
                or needle in (row.get('code') or '').lower()
                or needle in (row.get('owner_email') or '').lower()
                or needle in (row.get('address') or '').lower()
            ]
        return rows

    def get_franchise(self, franchise_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('franchises')
            .select(FRANCHISE_COLUMNS)
            .eq('id', str(franchise_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def get_franchise_by_code(self, code: str) -> dict[str, Any] | None:
        response = (
            self._db.table('franchises')
            .select(FRANCHISE_COLUMNS)
            .eq('code', code)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def create_franchise(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._db.table('franchises')
            .insert(payload)
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError('Franchise insert returned no data')
        return rows[0]

    def update_franchise(self, franchise_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._db.table('franchises')
            .update(payload)
            .eq('id', str(franchise_id))
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError('Franchise update returned no data')
        return rows[0]

    def list_owners_for_franchises(self, franchise_ids: list[str]) -> list[dict[str, Any]]:
        if not franchise_ids:
            return []
        response = (
            self._db.table('profiles')
            .select('id, full_name, phone, is_active, franchise_id, role')
            .eq('role', 'FRANCHISE_OWNER')
            .eq('is_active', True)
            .in_('franchise_id', franchise_ids)
            .execute()
        )
        return list(response.data or [])

    def get_profile(self, profile_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('profiles')
            .select('id, full_name, phone, is_active, franchise_id, role')
            .eq('id', str(profile_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def find_auth_user_id_by_email(self, email: str) -> str | None:
        """Resolve auth.users id via Supabase Auth Admin API (service role)."""
        normalized = email.strip().lower()
        try:
            # supabase-py >=2: list_users returns UsersResponse with .users
            page = 1
            per_page = 200
            while page <= 10:
                result = self._db.auth.admin.list_users(page=page, per_page=per_page)
                users = getattr(result, 'users', None) or []
                for user in users:
                    user_email = (getattr(user, 'email', None) or '').strip().lower()
                    if user_email == normalized:
                        return str(user.id)
                if len(users) < per_page:
                    break
                page += 1
        except TypeError:
            # Older client signature without pagination kwargs
            result = self._db.auth.admin.list_users()
            users = getattr(result, 'users', None) or []
            for user in users:
                user_email = (getattr(user, 'email', None) or '').strip().lower()
                if user_email == normalized:
                    return str(user.id)
        return None

    def invite_auth_user(
        self,
        *,
        email: str,
        full_name: str,
        redirect_to: str,
    ) -> Any:
        """Create Auth user and send Supabase invite/password-setup email."""
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
        """Fallback Auth user creation when invite email is unavailable."""
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

    def delete_auth_user(self, user_id: str) -> None:
        self._db.auth.admin.delete_user(user_id)

    def create_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._db.table('profiles').insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError('Profile insert returned no data')
        return rows[0]

    def get_active_owner(self, franchise_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('profiles')
            .select('id, full_name, phone, is_active, franchise_id, role')
            .eq('franchise_id', str(franchise_id))
            .eq('role', 'FRANCHISE_OWNER')
            .eq('is_active', True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

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

    def list_applications_for_franchise(self, franchise_id: UUID) -> list[dict[str, Any]]:
        response = (
            self._db.table('franchise_applications')
            .select(
                'id, applicant_name, email, phone, city, state, investment_range, message, '
                'status, reviewed_at, created_at, updated_at, converted_franchise_id'
            )
            .eq('converted_franchise_id', str(franchise_id))
            .order('created_at', desc=True)
            .execute()
        )
        return list(response.data or [])

    def list_applications(
        self,
        *,
        status: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self._db.table('franchise_applications').select(
            'id, applicant_name, email, phone, city, state, investment_range, message, '
            'status, reviewed_at, created_at, updated_at, converted_franchise_id'
        )
        if status:
            query = query.eq('status', status)
        response = query.order('created_at', desc=True).execute()
        rows = list(response.data or [])
        if search:
            needle = search.strip().lower()
            rows = [
                row
                for row in rows
                if needle in (row.get('applicant_name') or '').lower()
                or needle in (row.get('email') or '').lower()
                or needle in (row.get('city') or '').lower()
            ]
        return rows

    def get_application(self, application_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('franchise_applications')
            .select(
                'id, applicant_name, email, phone, city, state, investment_range, message, '
                'status, reviewed_at, created_at, updated_at, converted_franchise_id'
            )
            .eq('id', str(application_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def list_payments(self, franchise_id: UUID) -> list[dict[str, Any]]:
        response = (
            self._db.table('franchise_payments')
            .select(
                'id, franchise_id, amount, currency, payment_method, reference_number, '
                'status, paid_at, notes, created_at, updated_at'
            )
            .eq('franchise_id', str(franchise_id))
            .order('created_at', desc=True)
            .execute()
        )
        return list(response.data or [])

    def latest_payment_status_map(self, franchise_ids: list[str]) -> dict[str, str]:
        if not franchise_ids:
            return {}
        response = (
            self._db.table('franchise_payments')
            .select('franchise_id, status, created_at')
            .in_('franchise_id', franchise_ids)
            .order('created_at', desc=True)
            .execute()
        )
        result: dict[str, str] = {}
        for row in response.data or []:
            fid = str(row['franchise_id'])
            if fid not in result:
                result[fid] = str(row['status'])
        return result

    def list_checklist(self, franchise_id: UUID) -> list[dict[str, Any]]:
        response = (
            self._db.table('launch_checklist_items')
            .select(
                'id, franchise_id, item_key, item_name, display_order, is_completed, '
                'completed_at, completed_by, created_at, updated_at'
            )
            .eq('franchise_id', str(franchise_id))
            .order('display_order')
            .execute()
        )
        return list(response.data or [])

    def checklist_progress_map(self, franchise_ids: list[str]) -> dict[str, tuple[int, int]]:
        if not franchise_ids:
            return {}
        response = (
            self._db.table('launch_checklist_items')
            .select('franchise_id, is_completed')
            .in_('franchise_id', franchise_ids)
            .execute()
        )
        progress: dict[str, list[int]] = {fid: [0, 0] for fid in franchise_ids}
        for row in response.data or []:
            fid = str(row['franchise_id'])
            if fid not in progress:
                progress[fid] = [0, 0]
            progress[fid][1] += 1
            if row.get('is_completed'):
                progress[fid][0] += 1
        return {fid: (vals[0], vals[1]) for fid, vals in progress.items()}

    def seed_default_checklist(self, franchise_id: UUID) -> list[dict[str, Any]]:
        existing = self.list_checklist(franchise_id)
        if existing:
            return existing
        payload = [
            {
                'franchise_id': str(franchise_id),
                'item_key': item['item_key'],
                'item_name': item['item_name'],
                'display_order': item['display_order'],
                'is_completed': False,
            }
            for item in DEFAULT_LAUNCH_CHECKLIST
        ]
        response = self._db.table('launch_checklist_items').insert(payload).execute()
        return list(response.data or [])

    def update_checklist_item(
        self,
        franchise_id: UUID,
        item_id: UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        response = (
            self._db.table('launch_checklist_items')
            .update(payload)
            .eq('id', str(item_id))
            .eq('franchise_id', str(franchise_id))
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    @staticmethod
    def is_unique_violation(exc: Exception) -> bool:
        if isinstance(exc, APIError):
            # Postgres unique_violation = 23505
            code = getattr(exc, 'code', None) or ''
            message = str(exc)
            return code == '23505' or 'duplicate' in message.lower() or 'unique' in message.lower()
        message = str(exc).lower()
        return 'duplicate' in message or 'unique' in message
