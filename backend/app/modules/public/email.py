"""Resend HTTP delivery for public contact enquiries. No SDK."""

from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

RESEND_URL = 'https://api.resend.com/emails'
CONTACT_FAILURE_MESSAGE = 'Unable to send your enquiry right now. Please try again.'


class EmailDeliveryError(Exception):
    """Raised when the enquiry cannot be delivered."""


def _strip_header_value(value: str) -> str:
    return value.replace('\r', ' ').replace('\n', ' ').strip()


def send_contact_email(
    *,
    name: str,
    phone: str,
    email: str,
    message: str,
    enquiry_type: str = 'GENERAL',
) -> None:
    settings = get_settings()
    api_key = (settings.resend_api_key or '').strip()
    to_email = (settings.contact_to_email or '').strip()
    from_email = (settings.contact_from_email or '').strip()
    if not api_key or not to_email or not from_email:
        logger.error('Contact email is not configured')
        raise EmailDeliveryError(CONTACT_FAILURE_MESSAGE)

    safe_name = _strip_header_value(name)[:120]
    safe_type = _strip_header_value(enquiry_type)[:40]
    subject = _strip_header_value(f'RealStick Website Enquiry ({safe_type}) - {safe_name}')
    body = (
        f'Enquiry type: {safe_type}\n'
        f'Name: {name}\n'
        f'Phone: {phone}\n'
        f'Email: {email}\n'
        f'\n'
        f'Message:\n{message}\n'
    )

    try:
        response = httpx.post(
            RESEND_URL,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'from': from_email,
                'to': [to_email],
                'subject': subject,
                'text': body,
            },
            timeout=15.0,
        )
    except httpx.HTTPError:
        logger.exception('Resend request failed')
        raise EmailDeliveryError(CONTACT_FAILURE_MESSAGE) from None

    if response.status_code >= 400:
        logger.error('Resend rejected contact email status=%s', response.status_code)
        raise EmailDeliveryError(CONTACT_FAILURE_MESSAGE)
