"""Shared field validators used by Pydantic schemas.

Frontend mirrors these rules for UX. Backend remains authoritative.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
# After stripping spaces/hyphens: +91XXXXXXXXXX, 91XXXXXXXXXX, or XXXXXXXXXX.
# The 10-digit national number must start with 6-9 (Indian mobile).
_PHONE_RE = re.compile(r'^(?:\+91|91)?[6-9]\d{9}$')
_CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

INVALID_EMAIL = 'Invalid email format'
INVALID_PHONE = 'Enter a valid Indian phone number, such as +919876543210 or 9876543210.'
INVALID_MONEY = 'Enter a valid amount with up to 2 decimal places'
INVALID_PERCENTAGE = 'Enter a valid percentage with up to 2 decimal places'
INVALID_QUANTITY = 'Enter a valid whole number quantity'
BLANK_REQUIRED = 'This field is required'


def strip_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError('value must be a string')
    stripped = value.strip()
    return stripped or None


def validate_required_text(
    value: object,
    *,
    field_name: str = 'This field',
    max_length: int | None = None,
) -> str:
    stripped = strip_text(value)
    if not stripped:
        raise ValueError(f'{field_name} is required')
    if _CONTROL_RE.search(stripped):
        raise ValueError(f'{field_name} contains invalid characters')
    if max_length is not None and len(stripped) > max_length:
        raise ValueError(f'{field_name} must be at most {max_length} characters')
    return stripped


def validate_optional_text(
    value: object,
    *,
    field_name: str = 'This field',
    max_length: int | None = None,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError('value must be a string')
    stripped = value.strip()
    if not stripped:
        return None
    if _CONTROL_RE.search(stripped):
        raise ValueError(f'{field_name} contains invalid characters')
    if max_length is not None and len(stripped) > max_length:
        raise ValueError(f'{field_name} must be at most {max_length} characters')
    return stripped


def validate_email(value: object, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError('Email is required')
        return None
    if not isinstance(value, str):
        raise TypeError('email must be a string')
    stripped = value.strip().lower()
    if not stripped:
        if required:
            raise ValueError('Email is required')
        return None
    if not _EMAIL_RE.match(stripped):
        raise ValueError(INVALID_EMAIL)
    return stripped


def _compact_phone(value: str) -> str:
    return re.sub(r'[\s-]+', '', value.strip())


def validate_phone(value: object, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError('Phone is required')
        return None
    if not isinstance(value, str):
        raise TypeError('phone must be a string')
    stripped = value.strip()
    if not stripped:
        if required:
            raise ValueError('Phone is required')
        return None
    compact = _compact_phone(stripped)
    if not _PHONE_RE.fullmatch(compact):
        raise ValueError(INVALID_PHONE)
    return compact


def _parse_decimal(value: object, *, invalid_message: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(invalid_message)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError(invalid_message)
    try:
        amount = Decimal(str(value).strip()) if isinstance(value, str) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(invalid_message) from exc
    if not amount.is_finite():
        raise ValueError(invalid_message)
    return amount


def validate_money(
    value: object,
    *,
    field_name: str,
    required: bool = True,
    allow_zero: bool = False,
    min_value: Decimal | None = None,
    max_value: Decimal | None = None,
    invalid_message: str | None = None,
) -> Decimal | None:
    invalid = invalid_message or f'{field_name} must be a number with at most 2 decimal places'
    if value is None or value == '':
        if required:
            raise ValueError(f'{field_name} is required')
        return None
    amount = _parse_decimal(value, invalid_message=invalid)
    if amount.as_tuple().exponent < -2:
        raise ValueError(invalid)
    if amount < 0:
        raise ValueError(f'{field_name} cannot be negative')
    if not allow_zero and amount <= 0:
        raise ValueError(f'{field_name} must be greater than 0')
    if min_value is not None and amount < min_value:
        raise ValueError(f'{field_name} must be at least {min_value}')
    if max_value is not None and amount > max_value:
        raise ValueError(f'{field_name} must be at most {max_value}')
    return amount


def validate_price(
    value: object,
    *,
    field_name: str = 'Price',
    required: bool = True,
    allow_zero: bool = True,
) -> Decimal | None:
    return validate_money(
        value,
        field_name=field_name,
        required=required,
        allow_zero=allow_zero,
        invalid_message=f'{field_name} must be a number with at most 2 decimal places',
    )


def validate_amount(
    value: object,
    *,
    field_name: str = 'Amount',
    required: bool = True,
) -> Decimal | None:
    return validate_money(
        value,
        field_name=field_name,
        required=required,
        allow_zero=False,
        invalid_message=f'{field_name} must be a number with at most 2 decimal places',
    )


def validate_percentage(
    value: object,
    *,
    field_name: str = 'Percentage',
    required: bool = True,
    allow_zero: bool = True,
    min_value: Decimal = Decimal('0'),
    max_value: Decimal = Decimal('100'),
) -> Decimal | None:
    return validate_money(
        value,
        field_name=field_name,
        required=required,
        allow_zero=allow_zero,
        min_value=min_value,
        max_value=max_value,
        invalid_message=INVALID_PERCENTAGE,
    )


def validate_quantity(
    value: object,
    *,
    field_name: str = 'Quantity',
    minimum: int = 1,
    maximum: int = 999,
) -> int:
    if isinstance(value, bool):
        raise ValueError(INVALID_QUANTITY)
    try:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped or not re.fullmatch(r'\d+', stripped):
                raise ValueError(INVALID_QUANTITY)
            qty = int(stripped)
        else:
            qty = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(INVALID_QUANTITY) from exc
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(INVALID_QUANTITY)
    if qty < minimum or qty > maximum:
        raise ValueError(f'{field_name} must be between {minimum} and {maximum}')
    return qty
