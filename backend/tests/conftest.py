import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm

# Configure settings before application imports.
os.environ.setdefault('APP_ENV', 'test')
os.environ.setdefault('API_PREFIX', '/api/v1')
os.environ.setdefault('CORS_ORIGINS', 'http://localhost:5173')
os.environ.setdefault('SUPABASE_URL', 'https://example.supabase.co')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'test-service-role-key')
# Optional / unused for JWKS verification — retained for env compatibility.
os.environ.setdefault('SUPABASE_JWT_SECRET', 'unused-legacy-hs256-secret')
os.environ.setdefault('FRONTEND_APP_URL', 'http://localhost:5173')

from app.core.config import get_settings
from app.core.roles import UserRole
from app.core.security import clear_jwks_client_cache, decode_access_token
from app.db.supabase import get_supabase
from app.main import app


from tests.fake_db import FakeDatabase

ADMIN_ID = uuid4()
OWNER_ID = uuid4()
EMPLOYEE_ID = uuid4()
INACTIVE_ID = uuid4()
FRANCHISE_A = uuid4()
FRANCHISE_B = uuid4()
OWNER_CANDIDATE_ID = uuid4()
CATEGORY_ZEST = uuid4()
CATEGORY_GARDEN = uuid4()
CATEGORY_HARVEST = uuid4()
CATEGORY_RESERVE = uuid4()
CATEGORY_KULFI = uuid4()
CATEGORY_ROGUE = uuid4()  # unused extra category for delete/isolation tests
PRODUCT_NIMBU = uuid4()
PRODUCT_ORANGE = uuid4()
GST_SETTING_ID = uuid4()

TEST_KID = 'test-signing-key-1'
ROTATED_KID = 'test-signing-key-rotated'


def _profile(
    *,
    user_id,
    role: UserRole,
    franchise_id=None,
    is_active: bool = True,
    full_name: str = 'Test User',
    phone: str | None = None,
    login_id: str | None = None,
):
    now = datetime.now(timezone.utc).isoformat()
    return {
        'id': str(user_id),
        'full_name': full_name,
        'role': role.value,
        'franchise_id': str(franchise_id) if franchise_id else None,
        'phone': phone,
        'login_id': login_id,
        'is_active': is_active,
        'created_at': now,
        'updated_at': now,
    }


PROFILES = [
    _profile(user_id=ADMIN_ID, role=UserRole.SYSTEM_ADMIN, full_name='System Admin'),
    _profile(
        user_id=OWNER_ID,
        role=UserRole.FRANCHISE_OWNER,
        franchise_id=FRANCHISE_A,
        full_name='Franchise Owner',
    ),
    _profile(
        user_id=EMPLOYEE_ID,
        role=UserRole.EMPLOYEE,
        franchise_id=FRANCHISE_A,
        full_name='Employee User',
        login_id='EMP001',
    ),
    _profile(
        user_id=INACTIVE_ID,
        role=UserRole.EMPLOYEE,
        franchise_id=FRANCHISE_A,
        is_active=False,
        full_name='Inactive User',
        login_id='EMP000',
    ),
    _profile(
        user_id=OWNER_CANDIDATE_ID,
        role=UserRole.EMPLOYEE,
        franchise_id=FRANCHISE_B,
        full_name='Owner Candidate',
        login_id='EMP-CAND',
    ),
]


def _public_jwk(public_key, kid: str) -> dict:
    jwk = json.loads(ECAlgorithm.to_jwk(public_key))
    jwk.update({'kid': kid, 'alg': 'ES256', 'use': 'sig'})
    return jwk


@pytest.fixture(scope='session')
def es256_material():
    primary_private = ec.generate_private_key(ec.SECP256R1())
    rotated_private = ec.generate_private_key(ec.SECP256R1())
    return {
        'primary_private': primary_private,
        'rotated_private': rotated_private,
        'primary_jwk': _public_jwk(primary_private.public_key(), TEST_KID),
        'rotated_jwk': _public_jwk(rotated_private.public_key(), ROTATED_KID),
    }


@pytest.fixture
def jwks_state(es256_material):
    """Mutable JWKS document served to PyJWKClient during tests."""
    return {'keys': [es256_material['primary_jwk']], 'fetch_count': 0}


@pytest.fixture(autouse=True)
def _reset_caches_and_jwks(monkeypatch, jwks_state):
    get_settings.cache_clear()
    get_supabase.cache_clear()
    clear_jwks_client_cache()
    app.dependency_overrides.clear()

    class _JwksResponse(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=None, context=None):
        url = req.full_url if hasattr(req, 'full_url') else str(req)
        assert url.endswith('/auth/v1/.well-known/jwks.json')
        jwks_state['fetch_count'] += 1
        body = json.dumps({'keys': list(jwks_state['keys'])}).encode('utf-8')
        return _JwksResponse(body)

    monkeypatch.setattr(urllib.request, 'urlopen', fake_urlopen)

    yield

    app.dependency_overrides.clear()
    get_settings.cache_clear()
    get_supabase.cache_clear()
    clear_jwks_client_cache()


@pytest.fixture
def fake_db():
    from types import SimpleNamespace

    now = datetime.now(timezone.utc).isoformat()
    franchises = [
        {
            'id': str(FRANCHISE_A),
            'name': 'Hyderabad — Main Store',
            'code': 'HYD-MAIN',
            'owner_email': 'owner@realstick.in',
            'address': 'Shop 2 & 3, Hyderabad',
            'city': 'Hyderabad',
            'state': 'Telangana',
            'postal_code': None,
            'tier': 'Founder',
            'status': 'ACTIVE',
            'open_date': '2026-08-25',
            'closed_at': None,
            'employee_limit': 10,
            'settings': {},
            'is_archived': False,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(FRANCHISE_B),
            'name': 'Secunderabad Kiosk',
            'code': 'SEC-01',
            'owner_email': None,
            'address': 'Platform 1',
            'city': 'Secunderabad',
            'state': 'Telangana',
            'postal_code': None,
            'tier': 'Growth',
            'status': 'SETUP',
            'open_date': None,
            'closed_at': None,
            'employee_limit': 10,
            'settings': {},
            'is_archived': False,
            'created_at': now,
            'updated_at': now,
        },
    ]
    applications = [
        {
            'id': str(uuid4()),
            'applicant_name': 'Asha Reddy',
            'email': 'asha@example.com',
            'phone': '9999999999',
            'city': 'Hyderabad',
            'state': 'Telangana',
            'investment_range': '10-20L',
            'message': 'Interested in Founder tier',
            'status': 'CONVERTED',
            'reviewed_at': now,
            'converted_franchise_id': str(FRANCHISE_A),
            'created_at': now,
            'updated_at': now,
        }
    ]
    payments = [
        {
            'id': str(uuid4()),
            'franchise_id': str(FRANCHISE_A),
            'amount': 500000,
            'currency': 'INR',
            'payment_method': 'UPI',
            'reference_number': 'PAY-001',
            'status': 'COMPLETED',
            'paid_at': now,
            'notes': None,
            'created_at': now,
            'updated_at': now,
        }
    ]
    checklist = [
        {
            'id': str(uuid4()),
            'franchise_id': str(FRANCHISE_A),
            'item_key': 'agreement_signed',
            'item_name': 'Franchise agreement signed',
            'display_order': 1,
            'is_completed': True,
            'completed_at': now,
            'completed_by': str(ADMIN_ID),
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(uuid4()),
            'franchise_id': str(FRANCHISE_A),
            'item_key': 'fee_received',
            'item_name': 'Franchise fee received',
            'display_order': 2,
            'is_completed': False,
            'completed_at': None,
            'completed_by': None,
            'created_at': now,
            'updated_at': now,
        },
    ]
    auth_users = [
        SimpleNamespace(id=str(OWNER_ID), email='owner@realstick.in', password='OwnerPass12'),
        SimpleNamespace(id=str(OWNER_CANDIDATE_ID), email='candidate@realstick.in'),
        SimpleNamespace(id=str(ADMIN_ID), email='admin@realstick.in', password='AdminPass12'),
        SimpleNamespace(
            id=str(EMPLOYEE_ID),
            email='emp001@employees.invalid',
            password='EmpPass12',
        ),
        SimpleNamespace(id=str(INACTIVE_ID), email='emp000@employees.invalid'),
    ]
    product_categories = [
        {
            'id': str(CATEGORY_ZEST),
            'name': 'Zest Collection',
            'display_order': 1,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(CATEGORY_GARDEN),
            'name': 'Garden Collection',
            'display_order': 2,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(CATEGORY_HARVEST),
            'name': 'Harvest Collection',
            'display_order': 3,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(CATEGORY_RESERVE),
            'name': 'The Reserve',
            'display_order': 4,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(CATEGORY_KULFI),
            'name': 'Kulfi Heritage',
            'display_order': 5,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(CATEGORY_ROGUE),
            'name': 'Unused Test Category',
            'display_order': 99,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
    ]
    products = [
        {
            'id': str(PRODUCT_NIMBU),
            'category_id': str(CATEGORY_ZEST),
            'sku': None,
            'name': 'Nimbu Pudina',
            'description': 'Lemon & Fresh Mint',
            'image_url': None,
            'price': 100,
            'min_price': None,
            'max_price': None,
            'is_active': True,
            'metadata': {},
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(PRODUCT_ORANGE),
            'category_id': str(CATEGORY_GARDEN),
            'sku': None,
            'name': 'Nagpur Orange',
            'description': 'Vidarbha orange, pressed',
            'image_url': None,
            'price': 1200,
            'min_price': None,
            'max_price': None,
            'is_active': True,
            'metadata': {},
            'created_at': now,
            'updated_at': now,
        },
    ]
    franchise_product_prices = [
        {
            'id': str(uuid4()),
            'franchise_id': str(FRANCHISE_A),
            'product_id': str(PRODUCT_NIMBU),
            'selling_price': 22,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        }
    ]
    gst_settings = [
        {
            'id': str(GST_SETTING_ID),
            'rate': 5,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        }
    ]
    return FakeDatabase(
        profiles=PROFILES,
        franchises=franchises,
        applications=applications,
        payments=payments,
        checklist=checklist,
        product_categories=product_categories,
        products=products,
        franchise_product_prices=franchise_product_prices,
        gst_settings=gst_settings,
        auth_users=auth_users,
    )


@pytest.fixture
def client(monkeypatch, fake_db):
    monkeypatch.setattr('app.core.security.get_supabase', lambda: fake_db)
    monkeypatch.setattr('app.db.supabase.get_supabase', lambda: fake_db)
    monkeypatch.setattr('app.modules.franchises.repository.get_supabase', lambda: fake_db)
    monkeypatch.setattr('app.modules.products.repository.get_supabase', lambda: fake_db)
    monkeypatch.setattr('app.modules.users.repository.get_supabase', lambda: fake_db)
    monkeypatch.setattr('app.modules.pos.repository.get_supabase', lambda: fake_db)
    monkeypatch.setattr('app.modules.orders.repository.get_supabase', lambda: fake_db)
    monkeypatch.setattr('app.modules.reports.repository.get_supabase', lambda: fake_db)
    monkeypatch.setattr('app.modules.settings.repository.get_supabase', lambda: fake_db)
    monkeypatch.setattr('app.modules.public.repository.get_supabase', lambda: fake_db)
    monkeypatch.setattr('app.modules.gallery.repository.get_supabase', lambda: fake_db)
    return TestClient(app)


def make_access_token(
    *,
    user_id,
    email: str | None = 'user@realstick.in',
    private_key=None,
    kid: str = TEST_KID,
    issuer: str | None = None,
    audience: str | list[str] | None = 'authenticated',
    expires_delta: timedelta = timedelta(hours=1),
    include_sub: bool = True,
    es256_material=None,
) -> str:
    settings = get_settings()
    if private_key is None:
        if es256_material is None:
            raise RuntimeError('es256_material required when private_key is omitted')
        private_key = es256_material['primary_private']

    now = datetime.now(timezone.utc)
    payload: dict = {
        'email': email,
        'aud': audience,
        'role': 'authenticated',
        'iss': issuer if issuer is not None else settings.supabase_jwt_issuer,
        'iat': now,
        'exp': now + expires_delta,
    }
    if include_sub:
        payload['sub'] = str(user_id)

    headers = {'kid': kid, 'alg': 'ES256', 'typ': 'JWT'}
    return jwt.encode(payload, private_key, algorithm='ES256', headers=headers)


def auth_header(user_id, email: str, es256_material) -> dict[str, str]:
    token = make_access_token(user_id=user_id, email=email, es256_material=es256_material)
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def auth_header_factory(es256_material):
    def _factory(user_id, email: str) -> dict[str, str]:
        return auth_header(user_id, email, es256_material)

    return _factory
