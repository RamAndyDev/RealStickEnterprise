from tests.conftest import ADMIN_ID, EMPLOYEE_ID, OWNER_ID


def test_admin_can_login_with_email(client, fake_db):
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'admin@realstick.in', 'password': 'AdminPass12'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['access_token']
    assert body['refresh_token']
    assert 'password' not in body


def test_owner_can_login_with_email(client):
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'owner@realstick.in', 'password': 'OwnerPass12'},
    )
    assert response.status_code == 200
    assert response.json()['access_token']


def test_employee_can_login_with_user_id(client):
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'EMP001', 'password': 'EmpPass12'},
    )
    assert response.status_code == 200
    assert response.json()['access_token']


def test_employee_cannot_login_with_email(client):
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'emp001@employees.invalid', 'password': 'EmpPass12'},
    )
    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid credentials'


def test_employee_cannot_login_with_business_email(client):
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'employee@realstick.in', 'password': 'EmpPass12'},
    )
    assert response.status_code == 401


def test_wrong_password_is_rejected(client):
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'EMP001', 'password': 'wrong-password'},
    )
    assert response.status_code == 401


def test_login_never_returns_password(client):
    response = client.post(
        '/api/v1/auth/login',
        json={'identifier': 'EMP001', 'password': 'EmpPass12'},
    )
    assert 'EmpPass12' not in response.text
    assert 'password' not in response.json()


def test_employee_me_hides_email_and_shows_user_id(client, auth_header_factory):
    response = client.get(
        '/api/v1/auth/me',
        headers=auth_header_factory(EMPLOYEE_ID, 'emp001@employees.invalid'),
    )
    assert response.status_code == 200
    body = response.json()
    assert body['login_id'] == 'EMP001'
    assert body['email'] is None
    assert body['role'] == 'EMPLOYEE'


def test_admin_me_shows_email(client, auth_header_factory):
    response = client.get(
        '/api/v1/auth/me',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
    )
    assert response.json()['email'] == 'admin@realstick.in'
    assert response.json().get('login_id') in (None, '')
