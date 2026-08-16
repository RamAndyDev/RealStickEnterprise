from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.core.roles import UserRole
from tests.conftest import (
    ADMIN_ID,
    EMPLOYEE_ID,
    FRANCHISE_A,
    OWNER_CANDIDATE_ID,
    OWNER_ID,
)


def _admin(auth_header_factory):
    return auth_header_factory(ADMIN_ID, 'admin@realstick.in')


def _owner(auth_header_factory):
    return auth_header_factory(OWNER_ID, 'owner@realstick.in')


def _employee(auth_header_factory):
    return auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in')


def _seed_legacy_employee(
    fake_db,
    *,
    full_name: str = 'Ravi',
    password: str = 'ExistingPass12',
    franchise_id=FRANCHISE_A,
):
    user_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    fake_db.tables['profiles'].append(
        {
            'id': str(user_id),
            'full_name': full_name,
            'role': UserRole.EMPLOYEE.value,
            'franchise_id': str(franchise_id),
            'phone': '9000000001',
            'login_id': None,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        }
    )
    fake_db.auth.admin._users.append(
        SimpleNamespace(
            id=str(user_id),
            email=f'legacy-{user_id}@employees.invalid',
            password=password,
        )
    )
    return user_id


def test_owner_can_assign_user_id_to_existing_employee(client, auth_header_factory, fake_db):
    employee_id = _seed_legacy_employee(fake_db)
    auth_count = len(fake_db.auth.admin._users)
    profile_before = next(p for p in fake_db.tables['profiles'] if p['id'] == str(employee_id))
    auth_before = next(u for u in fake_db.auth.admin._users if str(u.id) == str(employee_id))

    response = client.patch(
        f'/api/v1/owner/employees/{employee_id}',
        headers=_owner(auth_header_factory),
        json={'login_id': 'EMP001R'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['login_id'] == 'EMP001R'
    assert body['full_name'] == 'Ravi'
    assert body['role'] == 'EMPLOYEE'
    assert body['franchise_id'] == str(FRANCHISE_A)
    assert body['is_active'] is True
    assert body['email'] is None
    assert 'employees.invalid' not in str(body).lower()

    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == str(employee_id))
    assert profile['login_id'] == 'EMP001R'
    assert profile['full_name'] == profile_before['full_name']
    assert profile['role'] == profile_before['role']
    assert profile['franchise_id'] == profile_before['franchise_id']
    assert profile['is_active'] is profile_before['is_active']
    assert profile['phone'] == profile_before['phone']

    auth_after = next(u for u in fake_db.auth.admin._users if str(u.id) == str(employee_id))
    assert getattr(auth_after, 'password', None) == 'ExistingPass12'
    assert auth_after.email == auth_before.email
    assert len(fake_db.auth.admin._users) == auth_count


def test_assigned_user_id_allows_employee_login(client, auth_header_factory, fake_db):
    employee_id = _seed_legacy_employee(fake_db, password='ExistingPass12')
    assigned = client.patch(
        f'/api/v1/owner/employees/{employee_id}',
        headers=_owner(auth_header_factory),
        json={'login_id': 'EMPRAVI'},
    )
    assert assigned.status_code == 200

    login = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'EMPRAVI', 'password': 'ExistingPass12'},
    )
    assert login.status_code == 200
    assert login.json()['access_token']

    hidden = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'empravi@employees.invalid', 'password': 'ExistingPass12'},
    )
    assert hidden.status_code == 401


def test_user_id_is_unique_case_insensitively(client, auth_header_factory, fake_db):
    employee_id = _seed_legacy_employee(fake_db)
    response = client.patch(
        f'/api/v1/owner/employees/{employee_id}',
        headers=_owner(auth_header_factory),
        json={'login_id': 'emp001'},
    )
    assert response.status_code == 409
    assert response.json()['detail'] == 'User ID is already in use'


def test_duplicate_user_id_returns_conflict(client, auth_header_factory, fake_db):
    employee_id = _seed_legacy_employee(fake_db)
    response = client.patch(
        f'/api/v1/owner/employees/{employee_id}',
        headers=_owner(auth_header_factory),
        json={'login_id': 'EMP001'},
    )
    assert response.status_code == 409
    assert 'already in use' in response.json()['detail']

    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == str(employee_id))
    assert profile['login_id'] is None


def test_empty_user_id_is_rejected(client, auth_header_factory, fake_db):
    employee_id = _seed_legacy_employee(fake_db)
    response = client.patch(
        f'/api/v1/owner/employees/{employee_id}',
        headers=_owner(auth_header_factory),
        json={'login_id': ''},
    )
    assert response.status_code == 422
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == str(employee_id))
    assert profile['login_id'] is None


def test_whitespace_only_user_id_is_rejected(client, auth_header_factory, fake_db):
    employee_id = _seed_legacy_employee(fake_db)
    response = client.patch(
        f'/api/v1/owner/employees/{employee_id}',
        headers=_owner(auth_header_factory),
        json={'login_id': '   '},
    )
    assert response.status_code == 422
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == str(employee_id))
    assert profile['login_id'] is None


def test_owner_can_update_employee_user_id_in_own_franchise(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}',
        headers=_owner(auth_header_factory),
        json={'login_id': 'EMP005'},
    )
    assert response.status_code == 200
    assert response.json()['login_id'] == 'EMP005'
    assert response.json()['franchise_id'] == str(FRANCHISE_A)


def test_owner_cannot_update_employee_user_id_from_another_franchise(
    client, auth_header_factory, fake_db
):
    before = next(p for p in fake_db.tables['profiles'] if p['id'] == str(OWNER_CANDIDATE_ID))
    response = client.patch(
        f'/api/v1/owner/employees/{OWNER_CANDIDATE_ID}',
        headers=_owner(auth_header_factory),
        json={'login_id': 'EMPCROSS'},
    )
    assert response.status_code == 403
    after = next(p for p in fake_db.tables['profiles'] if p['id'] == str(OWNER_CANDIDATE_ID))
    assert after['login_id'] == before['login_id']


def test_employee_cannot_update_own_user_id(client, auth_header_factory, fake_db):
    response = client.patch(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}',
        headers=_employee(auth_header_factory),
        json={'login_id': 'EMPHACK'},
    )
    assert response.status_code == 403
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == str(EMPLOYEE_ID))
    assert profile['login_id'] == 'EMP001'


def test_admin_employee_user_id_behavior_unchanged(client, auth_header_factory, fake_db):
    listed = client.get('/api/v1/admin/users', headers=_admin(auth_header_factory))
    assert listed.status_code == 200
    assert all(item['role'] != 'EMPLOYEE' for item in listed.json()['items'])

    admin_patch = client.patch(
        f'/api/v1/admin/users/{EMPLOYEE_ID}',
        headers=_admin(auth_header_factory),
        json={'login_id': 'EMPADMIN'},
    )
    assert admin_patch.status_code == 404

    owner_list = client.get('/api/v1/owner/employees', headers=_admin(auth_header_factory))
    assert owner_list.status_code == 403

    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == str(EMPLOYEE_ID))
    assert profile['login_id'] == 'EMP001'


def test_changing_user_id_replaces_login_without_resetting_password(
    client, auth_header_factory, fake_db
):
    auth_before = next(u for u in fake_db.auth.admin._users if str(u.id) == str(EMPLOYEE_ID))
    password_before = getattr(auth_before, 'password', None)
    auth_id_before = str(auth_before.id)
    email_before = auth_before.email
    auth_count = len(fake_db.auth.admin._users)

    response = client.patch(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}',
        headers=_owner(auth_header_factory),
        json={'login_id': 'EMP005'},
    )
    assert response.status_code == 200
    assert response.json()['login_id'] == 'EMP005'
    assert response.json()['full_name'] == 'Employee User'
    assert response.json()['email'] is None

    new_login = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'EMP005', 'password': 'EmpPass12'},
    )
    assert new_login.status_code == 200

    old_login = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'EMP001', 'password': 'EmpPass12'},
    )
    assert old_login.status_code == 401

    auth_after = next(u for u in fake_db.auth.admin._users if str(u.id) == str(EMPLOYEE_ID))
    assert str(auth_after.id) == auth_id_before
    assert getattr(auth_after, 'password', None) == password_before == 'EmpPass12'
    assert auth_after.email == email_before
    assert len(fake_db.auth.admin._users) == auth_count


def test_new_employee_creation_still_sets_login_id(client, auth_header_factory, fake_db):
    response = client.post(
        '/api/v1/owner/employees',
        headers=_owner(auth_header_factory),
        json={
            'full_name': 'Suresh',
            'login_id': 'EMPSURESH',
            'password': 'TestPass12',
            'confirm_password': 'TestPass12',
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body['user']['login_id'] == 'EMPSURESH'
    assert body['user']['email'] is None
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == body['user']['id'])
    assert profile['login_id'] == 'EMPSURESH'
    assert 'password' not in profile


def test_employee_email_stays_absent_after_user_id_assignment(
    client, auth_header_factory, fake_db
):
    employee_id = _seed_legacy_employee(fake_db, full_name='Meena')
    assigned = client.patch(
        f'/api/v1/owner/employees/{employee_id}',
        headers=_owner(auth_header_factory),
        json={'login_id': 'EMPMEENA'},
    )
    assert assigned.status_code == 200
    assert assigned.json()['email'] is None
    assert 'employees.invalid' not in assigned.text.lower()

    listed = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    match = next(item for item in listed.json()['items'] if item['id'] == str(employee_id))
    assert match['login_id'] == 'EMPMEENA'
    assert match['email'] is None
    assert all(item.get('email') in (None, '') for item in listed.json()['items'])
    assert 'employees.invalid' not in listed.text.lower()
