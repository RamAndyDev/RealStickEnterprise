from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from tests.conftest import (
    ADMIN_ID,
    EMPLOYEE_ID,
    FRANCHISE_A,
    FRANCHISE_B,
    INACTIVE_ID,
    OWNER_ID,
)


def _admin(auth_header_factory):
    return auth_header_factory(ADMIN_ID, 'admin@realstick.in')


def _owner(auth_header_factory):
    return auth_header_factory(OWNER_ID, 'owner@realstick.in')


def _employee(auth_header_factory):
    return auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in')


def _create_employee_payload(index: int, franchise_id=None):
    payload = {
        'full_name': f'Employee {index}',
        'login_id': f'EMP{index:03d}',
        'password': 'TestPass12',
        'confirm_password': 'TestPass12',
        'phone': f'90000000{index:02d}',
    }
    if franchise_id is not None:
        payload['franchise_id'] = str(franchise_id)
    return payload


# --- Authorization ---


def test_admin_can_list_users(client, auth_header_factory):
    response = client.get('/api/v1/admin/users', headers=_admin(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['total'] >= 2
    roles = {item['role'] for item in body['items']}
    assert 'SYSTEM_ADMIN' in roles
    assert 'FRANCHISE_OWNER' in roles
    assert 'EMPLOYEE' not in roles
    owner = next(item for item in body['items'] if item['id'] == str(OWNER_ID))
    assert owner['franchise_id'] == str(FRANCHISE_A)
    assert owner['franchise_name'] == 'Hyderabad — Main Store'
    assert owner['email'] == 'owner@realstick.in'
    assert 'password' not in owner


def test_owner_can_list_own_employees(client, auth_header_factory):
    response = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    ids = {item['id'] for item in body['items']}
    assert str(EMPLOYEE_ID) in ids
    assert str(OWNER_ID) not in ids
    assert str(ADMIN_ID) not in ids
    assert all(item['role'] == 'EMPLOYEE' for item in body['items'])
    assert all(item['franchise_id'] == str(FRANCHISE_A) for item in body['items'])
    assert all(item.get('email') in (None, '') for item in body['items'])
    employee = next(item for item in body['items'] if item['id'] == str(EMPLOYEE_ID))
    assert employee['login_id'] == 'EMP001'
    assert body['employee_limit'] == 10
    assert body['active_count'] >= 1


def test_employee_cannot_list_employees(client, auth_header_factory):
    owner_list = client.get('/api/v1/owner/employees', headers=_employee(auth_header_factory))
    admin_list = client.get('/api/v1/admin/users', headers=_employee(auth_header_factory))
    assert owner_list.status_code == 403
    assert admin_list.status_code == 403


def test_owner_cannot_access_another_franchise_employees(client, auth_header_factory):
    from tests.conftest import OWNER_CANDIDATE_ID

    response = client.get(
        f'/api/v1/owner/employees/{OWNER_CANDIDATE_ID}',
        headers=_owner(auth_header_factory),
    )
    assert response.status_code == 403

    listed = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    ids = {item['id'] for item in listed.json()['items']}
    assert str(OWNER_CANDIDATE_ID) not in ids


def test_employee_cannot_access_another_employee(client, auth_header_factory):
    from tests.conftest import OWNER_CANDIDATE_ID

    response = client.get(
        f'/api/v1/owner/employees/{OWNER_CANDIDATE_ID}',
        headers=_employee(auth_header_factory),
    )
    other = client.get(
        f'/api/v1/admin/users/{OWNER_CANDIDATE_ID}',
        headers=_employee(auth_header_factory),
    )
    me = client.get('/api/v1/auth/me', headers=_employee(auth_header_factory))
    assert response.status_code == 403
    assert other.status_code == 403
    assert me.status_code == 200
    assert me.json()['id'] == str(EMPLOYEE_ID)


def test_non_admin_cannot_create_system_admin(client, auth_header_factory):
    payload = {
        'full_name': 'Rogue Admin',
        'email': 'rogue.admin@realstick.in',
        'role': 'SYSTEM_ADMIN',
    }
    owner = client.post('/api/v1/admin/users', headers=_owner(auth_header_factory), json=payload)
    employee = client.post(
        '/api/v1/admin/users',
        headers=_employee(auth_header_factory),
        json=payload,
    )
    assert owner.status_code == 403
    assert employee.status_code == 403


def test_owner_cannot_create_system_admin(client, auth_header_factory, fake_db):
    response = client.post(
        '/api/v1/owner/employees',
        headers=_owner(auth_header_factory),
        json={
            'full_name': 'Not An Admin',
            'login_id': 'EMPROGUE',
            'password': 'TestPass12',
            'role': 'SYSTEM_ADMIN',
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body['user']['role'] == 'EMPLOYEE'
    assert body['user']['franchise_id'] == str(FRANCHISE_A)
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == body['user']['id'])
    assert profile['role'] == 'EMPLOYEE'


# --- Owner management (admin) ---


def test_admin_can_create_owner(client, auth_header_factory, fake_db):
    response = client.post(
        '/api/v1/admin/users',
        headers=_admin(auth_header_factory),
        json={
            'full_name': 'New Owner',
            'email': 'new.owner.m5@realstick.in',
            'phone': '9111111111',
            'role': 'FRANCHISE_OWNER',
            'franchise_id': str(FRANCHISE_B),
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert 'password' not in body
    assert 'password' not in body['user']
    assert body['password_setup'] in {'invite_email_sent', 'recovery_email_sent'}
    assert body['user']['role'] == 'FRANCHISE_OWNER'
    assert body['user']['franchise_id'] == str(FRANCHISE_B)
    assert body['user']['is_active'] is True
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == body['user']['id'])
    assert profile['role'] == 'FRANCHISE_OWNER'
    assert 'password' not in profile
    assert any(item['email'] == 'new.owner.m5@realstick.in' for item in fake_db.auth.admin.invites)


def test_admin_can_modify_owner(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/admin/users/{OWNER_ID}',
        headers=_admin(auth_header_factory),
        json={'full_name': 'Updated Owner', 'phone': '9000000001'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['full_name'] == 'Updated Owner'
    assert body['phone'] == '9000000001'
    assert body['role'] == 'FRANCHISE_OWNER'
    assert body['franchise_id'] == str(FRANCHISE_A)


def test_admin_can_deactivate_owner(client, auth_header_factory, fake_db):
    response = client.patch(
        f'/api/v1/admin/users/{OWNER_ID}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert response.status_code == 200
    assert response.json()['is_active'] is False
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == str(OWNER_ID))
    assert profile['is_active'] is False
    assert any(str(u.id) == str(OWNER_ID) for u in fake_db.auth.admin._users)


def test_admin_can_reset_owner_password(client, auth_header_factory, fake_db):
    response = client.post(
        f'/api/v1/admin/users/{OWNER_ID}/reset-password',
        headers=_admin(auth_header_factory),
    )
    assert response.status_code == 200
    body = response.json()
    assert body['password_setup'] == 'recovery_email_sent'
    assert 'password' not in body
    assert any(item['email'] == 'owner@realstick.in' for item in fake_db.auth.recovery_emails)


def test_only_one_active_owner_per_franchise(client, auth_header_factory, fake_db):
    created = client.post(
        '/api/v1/admin/users',
        headers=_admin(auth_header_factory),
        json={
            'full_name': 'Replacement Owner',
            'email': 'replacement.m5@realstick.in',
            'role': 'FRANCHISE_OWNER',
            'franchise_id': str(FRANCHISE_A),
        },
    )
    assert created.status_code == 201
    previous = next(p for p in fake_db.tables['profiles'] if p['id'] == str(OWNER_ID))
    assert previous['is_active'] is False
    active = [
        p
        for p in fake_db.tables['profiles']
        if p.get('role') == 'FRANCHISE_OWNER'
        and p.get('is_active')
        and str(p.get('franchise_id')) == str(FRANCHISE_A)
    ]
    assert len(active) == 1
    assert active[0]['id'] == created.json()['user']['id']


def test_admin_can_reassign_owner(client, auth_header_factory, fake_db):
    response = client.patch(
        f'/api/v1/admin/users/{OWNER_ID}',
        headers=_admin(auth_header_factory),
        json={'franchise_id': str(FRANCHISE_B)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['franchise_id'] == str(FRANCHISE_B)
    assert body['role'] == 'FRANCHISE_OWNER'
    assert body['is_active'] is True
    active_a = [
        p
        for p in fake_db.tables['profiles']
        if p.get('role') == 'FRANCHISE_OWNER'
        and p.get('is_active')
        and str(p.get('franchise_id')) == str(FRANCHISE_A)
    ]
    assert active_a == []


def test_admin_can_manage_system_admins(client, auth_header_factory, fake_db):
    created = client.post(
        '/api/v1/admin/users',
        headers=_admin(auth_header_factory),
        json={
            'full_name': 'Second Admin',
            'email': 'second.admin@realstick.in',
            'role': 'SYSTEM_ADMIN',
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body['user']['role'] == 'SYSTEM_ADMIN'
    assert body['user']['franchise_id'] is None
    assert 'password' not in body

    user_id = body['user']['id']
    updated = client.patch(
        f'/api/v1/admin/users/{user_id}',
        headers=_admin(auth_header_factory),
        json={'full_name': 'Second Admin Updated', 'is_active': False},
    )
    assert updated.status_code == 200
    assert updated.json()['full_name'] == 'Second Admin Updated'
    assert updated.json()['is_active'] is False

    reset = client.post(
        f'/api/v1/admin/users/{user_id}/reset-password',
        headers=_admin(auth_header_factory),
    )
    assert reset.status_code == 200
    assert reset.json()['password_setup'] == 'recovery_email_sent'


def test_admin_cannot_assign_system_admin_to_franchise(client, auth_header_factory):
    create = client.post(
        '/api/v1/admin/users',
        headers=_admin(auth_header_factory),
        json={
            'full_name': 'Admin With Franchise',
            'email': 'admin.franchise@realstick.in',
            'role': 'SYSTEM_ADMIN',
            'franchise_id': str(FRANCHISE_A),
        },
    )
    assert create.status_code == 422

    patch = client.patch(
        f'/api/v1/admin/users/{ADMIN_ID}',
        headers=_admin(auth_header_factory),
        json={'franchise_id': str(FRANCHISE_A)},
    )
    assert patch.status_code == 400


# --- Employee management (owner) ---


def test_owner_can_create_employee(client, auth_header_factory, fake_db):
    response = client.post(
        '/api/v1/owner/employees',
        headers=_owner(auth_header_factory),
        json={
            'full_name': 'Priya Shah',
            'login_id': 'EMPPRIYA',
            'password': 'TestPass12',
            'confirm_password': 'TestPass12',
            'phone': '9888888888',
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert 'password' not in body
    assert 'password' not in body['user']
    assert body['user']['role'] == 'EMPLOYEE'
    assert body['user']['login_id'] == 'EMPPRIYA'
    assert body['user']['email'] is None
    assert body['user']['franchise_id'] == str(FRANCHISE_A)
    assert body['user']['is_active'] is True
    assert body['password_setup'] == 'password_set'
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == body['user']['id'])
    assert profile['role'] == 'EMPLOYEE'
    assert profile['franchise_id'] == str(FRANCHISE_A)
    assert profile['login_id'] == 'EMPPRIYA'
    assert 'password' not in profile
    assert any(str(u.email) == 'emppriya@employees.invalid' for u in fake_db.auth.admin._users)


def test_employee_is_created_without_email(client, auth_header_factory, fake_db):
    response = client.post(
        '/api/v1/owner/employees',
        headers=_owner(auth_header_factory),
        json={'full_name': 'Fallback Hire', 'login_id': 'EMPFALL', 'password': 'TestPass12'},
    )
    assert response.status_code == 201
    body = response.json()
    assert body['password_setup'] == 'password_set'
    assert body['user']['email'] is None
    assert body['user']['login_id'] == 'EMPFALL'
    assert not fake_db.auth.recovery_emails


def test_employee_profile_role_is_employee(client, auth_header_factory):
    response = client.post(
        '/api/v1/owner/employees',
        headers=_owner(auth_header_factory),
        json={'full_name': 'Role Check', 'login_id': 'EMPROLE', 'password': 'TestPass12'},
    )
    assert response.status_code == 201
    assert response.json()['user']['role'] == 'EMPLOYEE'


def test_employee_franchise_matches_authenticated_owner(client, auth_header_factory):
    response = client.post(
        '/api/v1/owner/employees',
        headers=_owner(auth_header_factory),
        json={'full_name': 'Same Franchise', 'login_id': 'EMPSAME', 'password': 'TestPass12'},
    )
    assert response.status_code == 201
    assert response.json()['user']['franchise_id'] == str(FRANCHISE_A)


def test_owner_cannot_specify_a_different_franchise_id(client, auth_header_factory):
    response = client.post(
        '/api/v1/owner/employees',
        headers=_owner(auth_header_factory),
        json={
            'full_name': 'Wrong Franchise',
            'login_id': 'EMPWRONG',
            'password': 'TestPass12',
            'franchise_id': str(FRANCHISE_B),
        },
    )
    assert response.status_code == 201
    assert response.json()['user']['franchise_id'] == str(FRANCHISE_A)


def test_owner_can_modify_employee(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}',
        headers=_owner(auth_header_factory),
        json={'full_name': 'Employee Updated', 'phone': '9111111100'},
    )
    assert response.status_code == 200
    assert response.json()['full_name'] == 'Employee Updated'
    assert response.json()['phone'] == '9111111100'
    assert response.json()['role'] == 'EMPLOYEE'


def test_owner_can_deactivate_employee(client, auth_header_factory, fake_db):
    response = client.patch(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}',
        headers=_owner(auth_header_factory),
        json={'is_active': False},
    )
    assert response.status_code == 200
    assert response.json()['is_active'] is False
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == str(EMPLOYEE_ID))
    assert profile['is_active'] is False
    assert any(p['id'] == str(EMPLOYEE_ID) for p in fake_db.tables['profiles'])


def test_owner_can_reactivate_employee(client, auth_header_factory):
    client.patch(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}',
        headers=_owner(auth_header_factory),
        json={'is_active': False},
    )
    response = client.patch(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}',
        headers=_owner(auth_header_factory),
        json={'is_active': True},
    )
    assert response.status_code == 200
    assert response.json()['is_active'] is True


def test_owner_can_reset_employee_password(client, auth_header_factory, fake_db):
    response = client.post(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}/reset-password',
        headers=_owner(auth_header_factory),
        json={'new_password': 'NewEmpPass12', 'confirm_password': 'NewEmpPass12'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['password_setup'] == 'password_set'
    assert 'password' not in body
    assert 'NewEmpPass12' not in str(body)
    employee_auth = next(u for u in fake_db.auth.admin._users if str(u.id) == str(EMPLOYEE_ID))
    assert getattr(employee_auth, 'password', None) == 'NewEmpPass12'
    assert not fake_db.auth.recovery_emails


def test_employee_cannot_modify_another_employee(client, auth_header_factory):
    from tests.conftest import OWNER_CANDIDATE_ID

    owner_path = client.patch(
        f'/api/v1/owner/employees/{OWNER_CANDIDATE_ID}',
        headers=_employee(auth_header_factory),
        json={'full_name': 'Hacked'},
    )
    admin_path = client.patch(
        f'/api/v1/admin/users/{OWNER_CANDIDATE_ID}',
        headers=_employee(auth_header_factory),
        json={'full_name': 'Hacked'},
    )
    assert owner_path.status_code == 403
    assert admin_path.status_code == 403


def test_employee_cannot_change_own_password(client, auth_header_factory, fake_db):
    response = client.post(
        '/api/v1/auth/change-password',
        headers=_employee(auth_header_factory),
        json={'new_password': 'new-secret-99'},
    )
    assert response.status_code == 403
    employee_auth = next(u for u in fake_db.auth.admin._users if str(u.id) == str(EMPLOYEE_ID))
    assert getattr(employee_auth, 'password', None) != 'new-secret-99'


def test_owner_can_change_own_password(client, auth_header_factory, fake_db):
    response = client.post(
        '/api/v1/auth/change-password',
        headers=_owner(auth_header_factory),
        json={'new_password': 'new-secret-99'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['message'] == 'Password updated'
    assert 'new-secret-99' not in str(body)
    owner_auth = next(u for u in fake_db.auth.admin._users if str(u.id) == str(OWNER_ID))
    assert getattr(owner_auth, 'password', None) == 'new-secret-99'


def test_unauthenticated_change_password_is_rejected(client):
    response = client.post(
        '/api/v1/auth/change-password',
        json={'new_password': 'new-secret-99'},
    )
    assert response.status_code == 401


def test_change_password_rejects_short_password(client, auth_header_factory, fake_db):
    response = client.post(
        '/api/v1/auth/change-password',
        headers=_owner(auth_header_factory),
        json={'new_password': 'short'},
    )
    assert response.status_code == 422
    owner_auth = next(u for u in fake_db.auth.admin._users if str(u.id) == str(OWNER_ID))
    assert getattr(owner_auth, 'password', None) != 'short'


def test_change_password_is_not_stored_on_profile(client, auth_header_factory, fake_db):
    response = client.post(
        '/api/v1/auth/change-password',
        headers=_owner(auth_header_factory),
        json={'new_password': 'profile-safe-99'},
    )
    assert response.status_code == 200
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == str(OWNER_ID))
    assert 'password' not in profile
    assert 'new_password' not in profile
    assert 'profile-safe-99' not in str(profile)
    assert all('password' not in str(key).lower() for key in profile)



# --- Limit ---


def test_first_active_employee_can_be_created(client, auth_header_factory, fake_db):
    from tests.conftest import OWNER_CANDIDATE_ID

    fake_db.tables['profiles'] = [
        p for p in fake_db.tables['profiles'] if p['id'] != str(OWNER_CANDIDATE_ID)
    ]
    owner = client.post(
        '/api/v1/admin/users',
        headers=_admin(auth_header_factory),
        json={
            'full_name': 'Franchise B Owner',
            'email': 'franchise.b.owner@realstick.in',
            'role': 'FRANCHISE_OWNER',
            'franchise_id': str(FRANCHISE_B),
        },
    )
    assert owner.status_code == 201
    owner_id = owner.json()['user']['id']
    response = client.post(
        '/api/v1/owner/employees',
        headers=auth_header_factory(owner_id, 'franchise.b.owner@realstick.in'),
        json={
            'full_name': 'First Hire',
            'login_id': 'EMPFIRST',
            'password': 'TestPass12',
        },
    )
    assert response.status_code == 201
    assert response.json()['user']['role'] == 'EMPLOYEE'
    assert response.json()['user']['franchise_id'] == str(FRANCHISE_B)
    assert response.json()['user']['is_active'] is True


def test_tenth_active_employee_can_be_created(client, auth_header_factory):
    # Seed already has 1 active employee on FRANCHISE_A.
    for index in range(2, 11):
        response = client.post(
            '/api/v1/owner/employees',
            headers=_owner(auth_header_factory),
            json=_create_employee_payload(index),
        )
        assert response.status_code == 201, response.json()
    listed = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    assert listed.json()['active_count'] == 10


def test_eleventh_active_employee_is_rejected(client, auth_header_factory):
    for index in range(2, 11):
        created = client.post(
            '/api/v1/owner/employees',
            headers=_owner(auth_header_factory),
            json=_create_employee_payload(index),
        )
        assert created.status_code == 201
    response = client.post(
        '/api/v1/owner/employees',
        headers=_owner(auth_header_factory),
        json=_create_employee_payload(11),
    )
    assert response.status_code == 409
    assert '10' in response.json()['detail']


def test_deactivated_employee_does_not_count_toward_limit(client, auth_header_factory):
    for index in range(2, 11):
        assert (
            client.post(
                '/api/v1/owner/employees',
                headers=_owner(auth_header_factory),
                json=_create_employee_payload(index),
            ).status_code
            == 201
        )
    listed = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    active = [item for item in listed.json()['items'] if item['is_active']]
    assert len(active) == 10
    deactivated = client.patch(
        f'/api/v1/owner/employees/{active[0]["id"]}',
        headers=_owner(auth_header_factory),
        json={'is_active': False},
    )
    assert deactivated.status_code == 200
    after = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    assert after.json()['active_count'] == 9


def test_new_employee_can_be_created_after_deactivation(client, auth_header_factory):
    for index in range(2, 11):
        assert (
            client.post(
                '/api/v1/owner/employees',
                headers=_owner(auth_header_factory),
                json=_create_employee_payload(index),
            ).status_code
            == 201
        )
    listed = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    target = next(item for item in listed.json()['items'] if item['is_active'])
    client.patch(
        f'/api/v1/owner/employees/{target["id"]}',
        headers=_owner(auth_header_factory),
        json={'is_active': False},
    )
    response = client.post(
        '/api/v1/owner/employees',
        headers=_owner(auth_header_factory),
        json=_create_employee_payload(12),
    )
    assert response.status_code == 201
    listed_after = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    assert listed_after.json()['active_count'] == 10


def test_concurrent_employee_creation_cannot_bypass_limit(client, auth_header_factory):
    for index in range(2, 11):
        assert (
            client.post(
                '/api/v1/owner/employees',
                headers=_owner(auth_header_factory),
                json=_create_employee_payload(index),
            ).status_code
            == 201
        )

    headers = _owner(auth_header_factory)

    def _create(suffix: int):
        return client.post(
            '/api/v1/owner/employees',
            headers=headers,
            json={
                'full_name': f'Race {suffix}',
                'login_id': f'EMPRACE{suffix}{uuid4().hex[:6]}',
                'password': 'TestPass12',
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(_create, [1, 2]))

    statuses = sorted(response.status_code for response in results)
    assert statuses == [409, 409]
    listed = client.get('/api/v1/owner/employees', headers=headers)
    assert listed.json()['active_count'] == 10


# --- Status ---


def test_inactive_employee_cannot_access_protected_api(client, auth_header_factory):
    me = client.get(
        '/api/v1/auth/me',
        headers=auth_header_factory(INACTIVE_ID, 'inactive@realstick.in'),
    )
    employees = client.get(
        '/api/v1/owner/employees',
        headers=auth_header_factory(INACTIVE_ID, 'inactive@realstick.in'),
    )
    assert me.status_code == 403
    assert employees.status_code == 403


def test_inactive_owner_cannot_access_protected_api(client, auth_header_factory, fake_db):
    for profile in fake_db.tables['profiles']:
        if profile['id'] == str(OWNER_ID):
            profile['is_active'] = False
    response = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    me = client.get('/api/v1/auth/me', headers=_owner(auth_header_factory))
    assert response.status_code == 403
    assert me.status_code == 403


def test_inactive_user_remains_in_database(client, auth_header_factory, fake_db):
    client.patch(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}',
        headers=_owner(auth_header_factory),
        json={'is_active': False},
    )
    profiles = fake_db.tables['profiles']
    assert any(p['id'] == str(EMPLOYEE_ID) and p['is_active'] is False for p in profiles)
    assert any(str(u.id) == str(EMPLOYEE_ID) for u in fake_db.auth.admin._users)
    listed = client.get(
        '/api/v1/owner/employees',
        headers=_owner(auth_header_factory),
    )
    match = next(item for item in listed.json()['items'] if item['id'] == str(EMPLOYEE_ID))
    assert match['is_active'] is False


# --- User delete ---


def _create_unused_admin(client, auth_header_factory, email: str = 'spare.admin@realstick.in'):
    response = client.post(
        '/api/v1/admin/users',
        headers=_admin(auth_header_factory),
        json={
            'full_name': 'Spare Admin',
            'email': email,
            'role': 'SYSTEM_ADMIN',
        },
    )
    assert response.status_code == 201
    return response.json()['user']


def test_admin_can_delete_unreferenced_user(client, auth_header_factory, fake_db):
    created = _create_unused_admin(client, auth_header_factory)
    user_id = created['id']
    response = client.delete(f'/api/v1/admin/users/{user_id}', headers=_admin(auth_header_factory))
    assert response.status_code == 204
    assert not any(row['id'] == user_id for row in fake_db.tables['profiles'])
    assert not any(str(user.id) == user_id for user in fake_db.auth.admin._users)
    missing = client.get(f'/api/v1/admin/users/{user_id}', headers=_admin(auth_header_factory))
    assert missing.status_code == 404


def test_non_admin_cannot_delete_user(client, auth_header_factory):
    created = _create_unused_admin(client, auth_header_factory, 'locked.admin@realstick.in')
    for headers in (_owner(auth_header_factory), _employee(auth_header_factory)):
        response = client.delete(f'/api/v1/admin/users/{created["id"]}', headers=headers)
        assert response.status_code == 403


def test_unknown_user_delete_returns_404(client, auth_header_factory):
    response = client.delete(f'/api/v1/admin/users/{uuid4()}', headers=_admin(auth_header_factory))
    assert response.status_code == 404
    assert response.json()['detail'] == 'User not found'


def test_employee_delete_via_admin_returns_404(client, auth_header_factory, fake_db):
    profiles_before = list(fake_db.tables['profiles'])
    response = client.delete(
        f'/api/v1/admin/users/{EMPLOYEE_ID}',
        headers=_admin(auth_header_factory),
    )
    assert response.status_code == 404
    assert fake_db.tables['profiles'] == profiles_before


def test_referenced_user_delete_returns_409(client, auth_header_factory, fake_db):
    from app.modules.users.schemas import USER_DELETE_BLOCKED_DETAIL

    created = _create_unused_admin(client, auth_header_factory, 'auditor.admin@realstick.in')
    user_id = created['id']
    fake_db.tables['launch_checklist_items'].append(
        {
            'id': str(uuid4()),
            'franchise_id': str(FRANCHISE_B),
            'item_key': 'owner_assigned',
            'item_name': 'Franchise owner assigned',
            'display_order': 3,
            'is_completed': True,
            'completed_by': user_id,
        }
    )
    checklist_before = list(fake_db.tables['launch_checklist_items'])
    response = client.delete(f'/api/v1/admin/users/{user_id}', headers=_admin(auth_header_factory))
    assert response.status_code == 409
    assert response.json()['detail'] == USER_DELETE_BLOCKED_DETAIL
    assert any(row['id'] == user_id for row in fake_db.tables['profiles'])
    assert any(str(user.id) == user_id for user in fake_db.auth.admin._users)
    assert fake_db.tables['launch_checklist_items'] == checklist_before
    profile = next(row for row in fake_db.tables['profiles'] if row['id'] == user_id)
    assert profile['is_active'] is True


def test_cannot_delete_own_account(client, auth_header_factory, fake_db):
    from app.modules.users.schemas import SELF_DELETE_DETAIL

    _create_unused_admin(client, auth_header_factory, 'peer.admin@realstick.in')
    response = client.delete(f'/api/v1/admin/users/{ADMIN_ID}', headers=_admin(auth_header_factory))
    assert response.status_code == 409
    assert response.json()['detail'] == SELF_DELETE_DETAIL
    assert any(row['id'] == str(ADMIN_ID) for row in fake_db.tables['profiles'])


def test_cannot_delete_last_active_admin(client, auth_header_factory, fake_db):
    from app.modules.users.schemas import LAST_ADMIN_DELETE_DETAIL

    response = client.delete(f'/api/v1/admin/users/{ADMIN_ID}', headers=_admin(auth_header_factory))
    assert response.status_code == 409
    assert response.json()['detail'] == LAST_ADMIN_DELETE_DETAIL
    assert any(row['id'] == str(ADMIN_ID) for row in fake_db.tables['profiles'])
    assert any(str(user.id) == str(ADMIN_ID) for user in fake_db.auth.admin._users)


def test_failed_auth_cleanup_restores_profile(client, auth_header_factory, fake_db, monkeypatch):
    created = _create_unused_admin(client, auth_header_factory, 'rollback.admin@realstick.in')
    user_id = created['id']

    def fail_auth(_user_id: str) -> None:
        raise RuntimeError('auth delete failed')

    monkeypatch.setattr(
        'app.modules.users.repository.UsersRepository.delete_auth_user',
        fail_auth,
    )
    response = client.delete(f'/api/v1/admin/users/{user_id}', headers=_admin(auth_header_factory))
    assert response.status_code == 503
    assert any(row['id'] == user_id for row in fake_db.tables['profiles'])
    assert any(str(user.id) == user_id for user in fake_db.auth.admin._users)
