"""Employee User ID helpers. Internal Auth identity is never shown as email."""

from __future__ import annotations

import re

EMPLOYEE_IDENTITY_DOMAIN = 'employees.invalid'
LOGIN_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{1,31}$')
INVALID_CREDENTIALS = 'Invalid credentials'


def normalize_login_id(value: str) -> str:
    return value.strip()


def validate_login_id(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError('User ID is required')
    normalized = normalize_login_id(value)
    if not normalized:
        raise ValueError('User ID is required')
    if '@' in normalized or not LOGIN_ID_RE.match(normalized):
        raise ValueError(
            'User ID must be 2–32 characters using letters, numbers, dot, underscore, or hyphen'
        )
    return normalized


def employee_auth_identity(login_id: str) -> str:
    """Supabase Auth still needs an identity value. This is not a business email."""
    return f'{validate_login_id(login_id).lower()}@{EMPLOYEE_IDENTITY_DOMAIN}'


def is_internal_employee_identity(email: str | None) -> bool:
    if not email:
        return False
    return email.strip().lower().endswith(f'@{EMPLOYEE_IDENTITY_DOMAIN}')


def looks_like_email(identifier: str) -> bool:
    return '@' in identifier.strip()
