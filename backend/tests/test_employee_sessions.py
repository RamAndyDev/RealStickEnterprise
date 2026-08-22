from datetime import datetime, timezone
from uuid import uuid4

from tests.conftest import ADMIN_ID, EMPLOYEE_ID, FRANCHISE_A, OWNER_CANDIDATE_ID, OWNER_ID

SESSION_A = str(uuid4())
SESSION_B = str(uuid4())


def _admin(auth_header_factory):
    return auth_header_factory(ADMIN_ID, 'admin@realstick.in')


def _owner(auth_header_factory):
    return auth_header_factory(OWNER_ID, 'owner@realstick.in')


def _employee(auth_header_factory, session_id=None):
    return auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in', session_id=session_id)


def _session_row(
    *,
    employee_id=EMPLOYEE_ID,
    auth_session_id=SESSION_A,
    status='ACTIVE',
    logout_at=None,
    login_at=None,
    name='Employee User',
):
    now = datetime.now(timezone.utc).isoformat()
    return {
        'id': str(uuid4()),
        'employee_id': str(employee_id),
        'employee_name_snapshot': name,
        'auth_session_id': auth_session_id,
        'login_at': login_at or now,
        'logout_at': logout_at,
        'status': status,
        'created_at': now,
        'updated_at': now,
    }


def test_employee_login_creates_session(client, fake_db):
    before = len(fake_db.tables['employee_sessions'])
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'EMP001', 'password': 'EmpPass12'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['access_token']
    assert body.get('employee_session_id')
    rows = fake_db.tables['employee_sessions']
    assert len(rows) == before + 1
    created = next(row for row in rows if row['id'] == body['employee_session_id'])
    assert created['employee_id'] == str(EMPLOYEE_ID)
    assert created['employee_name_snapshot'] == 'Employee User'
    assert created['status'] == 'ACTIVE'
    assert created['logout_at'] is None
    assert created['login_at']
    assert created['auth_session_id']


def test_admin_login_does_not_create_employee_session(client, fake_db):
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'admin@realstick.in', 'password': 'AdminPass12'},
    )
    assert response.status_code == 200
    assert response.json().get('employee_session_id') in (None, '')
    assert fake_db.tables['employee_sessions'] == []


def test_owner_login_does_not_create_employee_session(client, fake_db):
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'owner@realstick.in', 'password': 'OwnerPass12'},
    )
    assert response.status_code == 200
    assert response.json().get('employee_session_id') in (None, '')
    assert fake_db.tables['employee_sessions'] == []


def test_failed_login_does_not_create_employee_session(client, fake_db):
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'EMP001', 'password': 'wrong-password'},
    )
    assert response.status_code == 401
    assert fake_db.tables['employee_sessions'] == []


def test_logout_completes_the_correct_session(client, fake_db, auth_header_factory):
    keep = _session_row(auth_session_id=SESSION_B)
    target = _session_row(auth_session_id=SESSION_A)
    fake_db.tables['employee_sessions'] = [keep, target]

    response = client.post(
        '/api/v1/auth/employee-sessions/logout',
        headers=_employee(auth_header_factory, session_id=SESSION_A),
        json={},
    )
    assert response.status_code == 200
    assert response.json()['ok'] is True

    updated = {row['id']: row for row in fake_db.tables['employee_sessions']}
    assert updated[target['id']]['status'] == 'COMPLETED'
    assert updated[target['id']]['logout_at']
    assert updated[keep['id']]['status'] == 'ACTIVE'
    assert updated[keep['id']]['logout_at'] is None


def test_logout_without_active_session_does_not_fail(client, fake_db, auth_header_factory):
    response = client.post(
        '/api/v1/auth/employee-sessions/logout',
        headers=_employee(auth_header_factory, session_id=SESSION_A),
        json={},
    )
    assert response.status_code == 200
    assert response.json()['ok'] is True
    assert fake_db.tables['employee_sessions'] == []


def test_logout_does_not_close_another_device_session(client, fake_db, auth_header_factory):
    other_device = _session_row(auth_session_id=SESSION_B)
    this_device = _session_row(auth_session_id=SESSION_A)
    fake_db.tables['employee_sessions'] = [other_device, this_device]

    response = client.post(
        '/api/v1/auth/employee-sessions/logout',
        headers=_employee(auth_header_factory, session_id=SESSION_A),
        json={'employee_session_id': other_device['id']},
    )
    assert response.status_code == 200
    rows = {row['id']: row for row in fake_db.tables['employee_sessions']}
    assert rows[this_device['id']]['status'] == 'COMPLETED'
    assert rows[other_device['id']]['status'] == 'ACTIVE'


def test_admin_and_owner_logout_tracking_is_noop(client, fake_db, auth_header_factory):
    seeded = _session_row()
    fake_db.tables['employee_sessions'] = [seeded]
    admin = client.post(
        '/api/v1/auth/employee-sessions/logout',
        headers=_admin(auth_header_factory),
        json={},
    )
    owner = client.post(
        '/api/v1/auth/employee-sessions/logout',
        headers=_owner(auth_header_factory),
        json={},
    )
    assert admin.status_code == 200
    assert owner.status_code == 200
    assert fake_db.tables['employee_sessions'][0]['status'] == 'ACTIVE'
    assert fake_db.tables['employee_sessions'][0]['logout_at'] is None


def test_owner_can_list_own_employees_with_login_status(client, fake_db, auth_header_factory):
    other_franchise = _session_row(employee_id=OWNER_CANDIDATE_ID, auth_session_id=str(uuid4()))
    fake_db.tables['employee_sessions'] = [
        _session_row(auth_session_id=SESSION_A),
        other_franchise,
    ]
    response = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    ids = {item['id'] for item in body['items']}
    assert str(EMPLOYEE_ID) in ids
    assert str(OWNER_CANDIDATE_ID) not in ids
    assert all(item['franchise_id'] == str(FRANCHISE_A) for item in body['items'])
    employee = next(item for item in body['items'] if item['id'] == str(EMPLOYEE_ID))
    assert employee['full_name'] == 'Employee User'
    assert employee['login_id'] == 'EMP001'
    assert employee['is_logged_in'] is True
    assert 'auth_session_id' not in employee


def test_owner_can_retrieve_own_employee_activity(client, fake_db, auth_header_factory):
    completed = _session_row(
        auth_session_id=str(uuid4()),
        status='COMPLETED',
        logout_at=datetime.now(timezone.utc).isoformat(),
    )
    active = _session_row(auth_session_id=SESSION_A)
    fake_db.tables['employee_sessions'] = [completed, active]

    response = client.get(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}/sessions',
        headers=_owner(auth_header_factory),
    )
    assert response.status_code == 200
    body = response.json()
    assert body['employee_id'] == str(EMPLOYEE_ID)
    assert body['employee_name'] == 'Employee User'
    assert len(body['items']) == 2
    by_id = {item['id']: item for item in body['items']}
    assert by_id[active['id']]['status'] == 'ACTIVE'
    assert by_id[active['id']]['logout_at'] is None
    assert by_id[completed['id']]['status'] == 'COMPLETED'
    assert by_id[completed['id']]['logout_at']
    assert 'auth_session_id' not in body['items'][0]


def test_owner_session_history_defaults_to_ten(client, fake_db, auth_header_factory):
    rows = []
    for index in range(12):
        rows.append(
            _session_row(
                auth_session_id=str(uuid4()),
                status='COMPLETED',
                logout_at=datetime.now(timezone.utc).isoformat(),
                login_at=f'2026-08-{index + 1:02d}T09:00:00+00:00',
            )
        )
    fake_db.tables['employee_sessions'] = rows
    response = client.get(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}/sessions',
        headers=_owner(auth_header_factory),
    )
    assert response.status_code == 200
    assert len(response.json()['items']) == 10


def test_owner_cannot_view_another_franchise_employee(client, auth_header_factory):
    listed = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    ids = {item['id'] for item in listed.json()['items']}
    assert str(OWNER_CANDIDATE_ID) not in ids

    detail = client.get(
        f'/api/v1/owner/employees/{OWNER_CANDIDATE_ID}',
        headers=_owner(auth_header_factory),
    )
    assert detail.status_code == 403


def test_owner_cannot_view_another_franchise_employee_history(client, fake_db, auth_header_factory):
    fake_db.tables['employee_sessions'] = [
        _session_row(employee_id=OWNER_CANDIDATE_ID, auth_session_id=str(uuid4())),
    ]
    response = client.get(
        f'/api/v1/owner/employees/{OWNER_CANDIDATE_ID}/sessions',
        headers=_owner(auth_header_factory),
    )
    assert response.status_code == 403
    assert response.json().get('items') is None


def test_employee_cannot_access_tracking_apis(client, auth_header_factory):
    listed = client.get('/api/v1/owner/employees', headers=_employee(auth_header_factory))
    sessions = client.get(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}/sessions',
        headers=_employee(auth_header_factory),
    )
    other = client.get(
        f'/api/v1/owner/employees/{OWNER_CANDIDATE_ID}/sessions',
        headers=_employee(auth_header_factory),
    )
    assert listed.status_code == 403
    assert sessions.status_code == 403
    assert other.status_code == 403


def test_admin_cannot_access_owner_employee_tracking_apis(client, auth_header_factory):
    listed = client.get('/api/v1/owner/employees', headers=_admin(auth_header_factory))
    sessions = client.get(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}/sessions',
        headers=_admin(auth_header_factory),
    )
    removed_admin_list = client.get('/api/v1/admin/employees', headers=_admin(auth_header_factory))
    removed_admin_sessions = client.get(
        f'/api/v1/admin/employees/{EMPLOYEE_ID}/sessions',
        headers=_admin(auth_header_factory),
    )
    assert listed.status_code == 403
    assert sessions.status_code == 403
    assert removed_admin_list.status_code == 404
    assert removed_admin_sessions.status_code == 404


def test_owner_sessions_for_non_employee_returns_404(client, auth_header_factory):
    response = client.get(
        f'/api/v1/owner/employees/{OWNER_ID}/sessions',
        headers=_owner(auth_header_factory),
    )
    assert response.status_code == 404


def test_tracking_failure_does_not_block_authentication(client, fake_db, monkeypatch):
    def fail_insert(self, payload):
        raise RuntimeError('session insert failed')

    monkeypatch.setattr(
        'app.modules.employee_sessions.repository.EmployeeSessionsRepository.insert',
        fail_insert,
    )
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'EMP001', 'password': 'EmpPass12'},
    )
    assert response.status_code == 200
    assert response.json()['access_token']
    assert fake_db.tables['employee_sessions'] == []


def test_tracking_failure_does_not_block_logout(client, fake_db, auth_header_factory, monkeypatch):
    seeded = _session_row(auth_session_id=SESSION_A)
    fake_db.tables['employee_sessions'] = [seeded]

    def fail_complete(self, session_id, *, logout_at=None):
        raise RuntimeError('session update failed')

    monkeypatch.setattr(
        'app.modules.employee_sessions.repository.EmployeeSessionsRepository.complete',
        fail_complete,
    )
    response = client.post(
        '/api/v1/auth/employee-sessions/logout',
        headers=_employee(auth_header_factory, session_id=SESSION_A),
        json={},
    )
    assert response.status_code == 200
    assert response.json()['ok'] is True


def test_existing_admin_user_list_still_excludes_employees(client, auth_header_factory):
    response = client.get('/api/v1/admin/users', headers=_admin(auth_header_factory))
    assert response.status_code == 200
    roles = {item['role'] for item in response.json()['items']}
    assert 'EMPLOYEE' not in roles
