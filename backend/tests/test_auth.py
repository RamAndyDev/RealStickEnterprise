from datetime import timedelta
from uuid import uuid4

import jwt as pyjwt
import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.security import clear_jwks_client_cache, decode_access_token
from tests.conftest import (
    ADMIN_ID,
    EMPLOYEE_ID,
    FRANCHISE_A,
    FRANCHISE_B,
    INACTIVE_ID,
    OWNER_ID,
    ROTATED_KID,
    make_access_token,
)


def test_unauthenticated_me_returns_401(client):
    response = client.get('/api/v1/auth/me')
    assert response.status_code == 401


def test_valid_es256_token_accepted(client, auth_header_factory):
    response = client.get(
        '/api/v1/auth/me',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
    )
    assert response.status_code == 200
    assert response.json()['id'] == str(ADMIN_ID)


def test_invalid_signature_returns_401(client, es256_material):
    # Sign with a different private key while advertising the primary kid.
    token = make_access_token(
        user_id=ADMIN_ID,
        email='admin@realstick.in',
        private_key=es256_material['rotated_private'],
        kid=es256_material['primary_jwk']['kid'],
        es256_material=es256_material,
    )
    response = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401


def test_expired_token_returns_401(client, es256_material):
    token = make_access_token(
        user_id=ADMIN_ID,
        email='admin@realstick.in',
        expires_delta=timedelta(seconds=-10),
        es256_material=es256_material,
    )
    response = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401


def test_wrong_issuer_returns_401(client, es256_material):
    token = make_access_token(
        user_id=ADMIN_ID,
        email='admin@realstick.in',
        issuer='https://evil.example/auth/v1',
        es256_material=es256_material,
    )
    response = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401


def test_wrong_audience_returns_401(client, es256_material):
    token = make_access_token(
        user_id=ADMIN_ID,
        email='admin@realstick.in',
        audience='anon',
        es256_material=es256_material,
    )
    response = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401


def test_missing_subject_returns_401(client, es256_material):
    token = make_access_token(
        user_id=ADMIN_ID,
        email='admin@realstick.in',
        include_sub=False,
        es256_material=es256_material,
    )
    response = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401


def test_unknown_kid_triggers_jwks_refresh(monkeypatch, es256_material, jwks_state):
    import json
    import urllib.request
    from io import BytesIO

    clear_jwks_client_cache()
    fetches = {'n': 0}
    sequenced = [
        {'keys': [es256_material['primary_jwk']]},
        {'keys': [es256_material['rotated_jwk']]},
    ]

    class _Resp(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def sequenced_urlopen(req, timeout=None, context=None):
        idx = min(fetches['n'], len(sequenced) - 1)
        fetches['n'] += 1
        jwks_state['fetch_count'] = fetches['n']
        return _Resp(json.dumps(sequenced[idx]).encode('utf-8'))

    monkeypatch.setattr(urllib.request, 'urlopen', sequenced_urlopen)

    token = make_access_token(
        user_id=ADMIN_ID,
        email='admin@realstick.in',
        private_key=es256_material['rotated_private'],
        kid=ROTATED_KID,
        es256_material=es256_material,
    )

    payload = decode_access_token(token)
    assert payload['sub'] == str(ADMIN_ID)
    assert fetches['n'] >= 2  # cached set miss → refresh once


def test_system_admin_me_succeeds(client, auth_header_factory):
    response = client.get(
        '/api/v1/auth/me',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
    )
    assert response.status_code == 200
    body = response.json()
    assert body['id'] == str(ADMIN_ID)
    assert body['email'] == 'admin@realstick.in'
    assert body['full_name'] == 'System Admin'
    assert body['role'] == 'SYSTEM_ADMIN'
    assert body['franchise_id'] is None
    assert body['is_active'] is True
    assert 'token' not in body
    assert 'password' not in body


def test_inactive_profile_returns_403(client, auth_header_factory):
    response = client.get(
        '/api/v1/auth/me',
        headers=auth_header_factory(INACTIVE_ID, 'inactive@realstick.in'),
    )
    assert response.status_code == 403


def test_system_admin_can_access_admin_endpoint(client, auth_header_factory):
    response = client.get(
        '/api/v1/auth/test/admin',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
    )
    assert response.status_code == 200
    assert response.json()['role'] == 'SYSTEM_ADMIN'


def test_franchise_owner_denied_admin_endpoint(client, auth_header_factory):
    response = client.get(
        '/api/v1/auth/test/admin',
        headers=auth_header_factory(OWNER_ID, 'owner@realstick.in'),
    )
    assert response.status_code == 403


def test_employee_denied_admin_endpoint(client, auth_header_factory):
    response = client.get(
        '/api/v1/auth/test/admin',
        headers=auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in'),
    )
    assert response.status_code == 403


def test_franchise_owner_cannot_access_another_franchise(client, auth_header_factory):
    allowed = client.get(
        f'/api/v1/auth/test/franchise/{FRANCHISE_A}',
        headers=auth_header_factory(OWNER_ID, 'owner@realstick.in'),
    )
    denied = client.get(
        f'/api/v1/auth/test/franchise/{FRANCHISE_B}',
        headers=auth_header_factory(OWNER_ID, 'owner@realstick.in'),
    )
    assert allowed.status_code == 200
    assert denied.status_code == 403


def test_employee_cannot_access_another_franchise(client, auth_header_factory):
    allowed = client.get(
        f'/api/v1/auth/test/franchise/{FRANCHISE_A}',
        headers=auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in'),
    )
    denied = client.get(
        f'/api/v1/auth/test/franchise/{FRANCHISE_B}',
        headers=auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in'),
    )
    assert allowed.status_code == 200
    assert denied.status_code == 403


def test_system_admin_can_access_any_franchise(client, auth_header_factory):
    response = client.get(
        f'/api/v1/auth/test/franchise/{uuid4()}',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
    )
    assert response.status_code == 200


def test_decode_rejects_hs256_token():
    from datetime import datetime, timezone

    settings = get_settings()
    now = datetime.now(timezone.utc)
    hs_token = pyjwt.encode(
        {
            'sub': str(ADMIN_ID),
            'email': 'admin@realstick.in',
            'aud': 'authenticated',
            'role': 'authenticated',
            'iss': settings.supabase_jwt_issuer,
            'iat': now,
            'exp': now + timedelta(hours=1),
        },
        'unused-legacy-hs256-secret',
        algorithm='HS256',
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(hs_token)
    assert exc_info.value.status_code == 401
