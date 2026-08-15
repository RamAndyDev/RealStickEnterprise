from __future__ import annotations

import secrets
from typing import Any, Protocol

from fastapi import HTTPException, status

from app.core.config import get_settings


class AuthProvisionRepo(Protocol):
    def find_auth_user_id_by_email(self, email: str) -> str | None: ...

    def invite_auth_user(self, *, email: str, full_name: str, redirect_to: str) -> Any: ...

    def create_auth_user_with_temp_password(
        self,
        *,
        email: str,
        full_name: str,
        password: str,
    ) -> Any: ...

    def send_recovery_email(self, *, email: str, redirect_to: str) -> Any: ...

    def delete_auth_user(self, user_id: str) -> None: ...


class AuthProvisionResult:
    def __init__(self, auth_user_id: str, password_setup: str, message: str) -> None:
        self.auth_user_id = auth_user_id
        self.password_setup = password_setup
        self.message = message


def _extract_user_id(result: Any) -> str | None:
    user = getattr(result, 'user', None)
    if user is not None:
        user_id = getattr(user, 'id', None)
        if user_id:
            return str(user_id)
        if isinstance(user, dict) and user.get('id'):
            return str(user['id'])
    user_id = getattr(result, 'id', None)
    if user_id:
        return str(user_id)
    if isinstance(result, dict):
        nested = result.get('user') or result
        if isinstance(nested, dict) and nested.get('id'):
            return str(nested['id'])
    return None


def _already_exists(exc: Exception) -> bool:
    detail = str(exc).lower()
    return 'already' in detail or 'registered' in detail or 'exists' in detail


def send_password_recovery_email(repo: AuthProvisionRepo, *, email: str) -> None:
    """Send a Supabase Auth recovery email. Does not generate/log action links."""
    redirect_to = get_settings().password_reset_redirect_url
    try:
        repo.send_recovery_email(email=email, redirect_to=redirect_to)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Unable to initiate password reset',
        ) from exc


def provision_auth_user(
    repo: AuthProvisionRepo,
    *,
    email: str,
    full_name: str,
    created_label: str = 'User created',
    existing_conflict_detail: str = 'An auth user with this email already exists',
) -> AuthProvisionResult:
    """Create a Supabase Auth user and send a password-setup email.

    Primary path: admin invite (sends Invite email).
    Fallback: create confirmed user + POST /recover (sends Recovery email).

    generate_link is not used — it returns a URL and does not send email.
    """
    if repo.find_auth_user_id_by_email(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=existing_conflict_detail)

    redirect_to = get_settings().password_reset_redirect_url

    try:
        invited = repo.invite_auth_user(
            email=email,
            full_name=full_name,
            redirect_to=redirect_to,
        )
        auth_user_id = _extract_user_id(invited) or repo.find_auth_user_id_by_email(email)
        if not auth_user_id:
            raise RuntimeError('Invite succeeded but auth user id was not returned')
        return AuthProvisionResult(
            auth_user_id,
            'invite_email_sent',
            f'{created_label}. A password setup invite was sent to {email}.',
        )
    except HTTPException:
        raise
    except Exception as invite_exc:
        existing_id = repo.find_auth_user_id_by_email(email)
        if existing_id:
            try:
                repo.send_recovery_email(email=email, redirect_to=redirect_to)
            except Exception as send_exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail='Unable to send password setup email',
                ) from send_exc
            return AuthProvisionResult(
                existing_id,
                'recovery_email_sent',
                f'{created_label}. A password recovery email was sent to {email}.',
            )
        if _already_exists(invite_exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=existing_conflict_detail,
            ) from invite_exc

        created_id: str | None = None
        try:
            created = repo.create_auth_user_with_temp_password(
                email=email,
                full_name=full_name,
                password=secrets.token_urlsafe(32),
            )
            created_id = _extract_user_id(created) or repo.find_auth_user_id_by_email(email)
            if not created_id:
                raise RuntimeError('Auth user creation did not return an id')
            repo.send_recovery_email(email=email, redirect_to=redirect_to)
            return AuthProvisionResult(
                created_id,
                'recovery_email_sent',
                f'{created_label}. A password recovery email was sent to {email}.',
            )
        except HTTPException:
            raise
        except Exception as create_exc:
            if created_id:
                try:
                    repo.delete_auth_user(created_id)
                except Exception:
                    pass
            if _already_exists(create_exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=existing_conflict_detail,
                ) from create_exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to create auth user and send password setup email',
            ) from invite_exc
