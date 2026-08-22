"""Admin-controlled Franchise Owner Audit visibility."""

from __future__ import annotations

from copy import deepcopy

from tests.conftest import FRANCHISE_A, FRANCHISE_B
from tests.test_audits import _admin, _create, _create_payload, _employee, _owner

SETTING_PATH = '/api/v1/admin/settings/franchise-audit'


def _set_owner_audit(client, auth_header_factory, enabled: bool) -> dict:
    response = client.patch(
        SETTING_PATH,
        headers=_admin(auth_header_factory),
        json={'franchise_owner_audit_enabled': enabled},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_admin_can_read_franchise_audit_setting(client, auth_header_factory):
    response = client.get(SETTING_PATH, headers=_admin(auth_header_factory))
    assert response.status_code == 200
    assert response.json()['franchise_owner_audit_enabled'] is False


def test_admin_can_enable_and_disable_franchise_audit_setting(client, auth_header_factory):
    enabled = _set_owner_audit(client, auth_header_factory, True)
    assert enabled['franchise_owner_audit_enabled'] is True
    read = client.get(SETTING_PATH, headers=_admin(auth_header_factory))
    assert read.status_code == 200
    assert read.json()['franchise_owner_audit_enabled'] is True
    disabled = _set_owner_audit(client, auth_header_factory, False)
    assert disabled['franchise_owner_audit_enabled'] is False
    reread = client.get(SETTING_PATH, headers=_admin(auth_header_factory))
    assert reread.json()['franchise_owner_audit_enabled'] is False


def test_franchise_owner_cannot_update_franchise_audit_setting(client, auth_header_factory):
    response = client.patch(
        SETTING_PATH,
        headers=_owner(auth_header_factory),
        json={'franchise_owner_audit_enabled': True},
    )
    assert response.status_code == 403
    current = client.get(SETTING_PATH, headers=_admin(auth_header_factory))
    assert current.json()['franchise_owner_audit_enabled'] is False


def test_employee_cannot_update_franchise_audit_setting(client, auth_header_factory):
    response = client.patch(
        SETTING_PATH,
        headers=_employee(auth_header_factory),
        json={'franchise_owner_audit_enabled': True},
    )
    assert response.status_code == 403
    current = client.get(SETTING_PATH, headers=_admin(auth_header_factory))
    assert current.json()['franchise_owner_audit_enabled'] is False


def test_franchise_owner_and_employee_cannot_read_admin_setting(client, auth_header_factory):
    assert client.get(SETTING_PATH, headers=_owner(auth_header_factory)).status_code == 403
    assert client.get(SETTING_PATH, headers=_employee(auth_header_factory)).status_code == 403


def test_default_franchise_owner_audit_setting_is_disabled(client, auth_header_factory):
    response = client.get(SETTING_PATH, headers=_admin(auth_header_factory))
    assert response.status_code == 200
    assert response.json()['franchise_owner_audit_enabled'] is False


def test_missing_setting_falls_back_to_disabled(client, auth_header_factory, fake_db):
    fake_db.tables['system_settings'].clear()
    response = client.get(SETTING_PATH, headers=_admin(auth_header_factory))
    assert response.status_code == 200
    assert response.json()['franchise_owner_audit_enabled'] is False
    me = client.get('/api/v1/auth/me', headers=_owner(auth_header_factory))
    assert me.status_code == 200
    assert me.json()['franchise_owner_audit_enabled'] is False
    listed = client.get('/api/v1/audits', headers=_owner(auth_header_factory))
    assert listed.status_code == 403


def test_unavailable_setting_falls_back_to_disabled(client, auth_header_factory, monkeypatch):
    def _boom(_key: str):
        raise RuntimeError('system_settings unavailable')

    monkeypatch.setattr(
        'app.modules.settings.repository.SettingsRepository.get_system_setting',
        _boom,
    )
    response = client.get(SETTING_PATH, headers=_admin(auth_header_factory))
    assert response.status_code == 200
    assert response.json()['franchise_owner_audit_enabled'] is False
    me = client.get('/api/v1/auth/me', headers=_owner(auth_header_factory))
    assert me.status_code == 200
    assert me.json()['franchise_owner_audit_enabled'] is False
    listed = client.get('/api/v1/audits', headers=_owner(auth_header_factory))
    assert listed.status_code == 403


def test_new_installation_starts_with_franchise_owner_audit_disabled(
    client,
    auth_header_factory,
):
    me = client.get('/api/v1/auth/me', headers=_owner(auth_header_factory))
    assert me.status_code == 200
    assert me.json()['franchise_owner_audit_enabled'] is False
    listed = client.get('/api/v1/audits', headers=_owner(auth_header_factory))
    assert listed.status_code == 403
    created = client.post(
        '/api/v1/audits',
        headers=_owner(auth_header_factory),
        json=_create_payload(franchise_id=None),
    )
    assert created.status_code == 403


def test_auth_me_includes_franchise_owner_audit_setting(client, auth_header_factory):
    me = client.get('/api/v1/auth/me', headers=_owner(auth_header_factory))
    assert me.status_code == 200
    assert me.json()['franchise_owner_audit_enabled'] is False
    _set_owner_audit(client, auth_header_factory, True)
    me_enabled = client.get('/api/v1/auth/me', headers=_owner(auth_header_factory))
    assert me_enabled.status_code == 200
    assert me_enabled.json()['franchise_owner_audit_enabled'] is True


def test_owner_can_access_audit_after_admin_enables(client, auth_header_factory):
    _set_owner_audit(client, auth_header_factory, True)
    created = _create(client, _owner(auth_header_factory), franchise_id=None)
    listed = client.get('/api/v1/audits', headers=_owner(auth_header_factory))
    assert listed.status_code == 200
    assert listed.json()['total'] == 1
    detail = client.get(f'/api/v1/audits/{created["id"]}', headers=_owner(auth_header_factory))
    assert detail.status_code == 200
    assert detail.json()['id'] == created['id']


def test_owner_cannot_access_audit_when_disabled(client, auth_header_factory):
    created = _create(client, _admin(auth_header_factory))
    listed = client.get('/api/v1/audits', headers=_owner(auth_header_factory))
    assert listed.status_code == 403
    detail = client.get(f'/api/v1/audits/{created["id"]}', headers=_owner(auth_header_factory))
    assert detail.status_code == 403
    created_while_disabled = client.post(
        '/api/v1/audits',
        headers=_owner(auth_header_factory),
        json=_create_payload(franchise_id=None),
    )
    assert created_while_disabled.status_code == 403


def test_admin_can_access_audit_when_setting_disabled(client, auth_header_factory):
    created = _create(client, _admin(auth_header_factory))
    listed = client.get('/api/v1/audits', headers=_admin(auth_header_factory))
    assert listed.status_code == 200
    assert listed.json()['total'] == 1
    detail = client.get(f'/api/v1/audits/{created["id"]}', headers=_admin(auth_header_factory))
    assert detail.status_code == 200
    assert detail.json()['id'] == created['id']


def test_employee_remains_denied_when_setting_enabled_or_disabled(client, auth_header_factory):
    created = _create(client, _admin(auth_header_factory))
    assert client.get('/api/v1/audits', headers=_employee(auth_header_factory)).status_code == 403
    _set_owner_audit(client, auth_header_factory, True)
    assert client.get('/api/v1/audits', headers=_employee(auth_header_factory)).status_code == 403
    assert client.get(
        f'/api/v1/audits/{created["id"]}',
        headers=_employee(auth_header_factory),
    ).status_code == 403
    assert client.post(
        '/api/v1/audits',
        headers=_employee(auth_header_factory),
        json=_create_payload(),
    ).status_code == 403


def test_owner_cannot_access_another_franchise_audit_when_enabled(client, auth_header_factory):
    _set_owner_audit(client, auth_header_factory, True)
    other = _create(client, _admin(auth_header_factory), franchise_id=str(FRANCHISE_B))
    response = client.get(f'/api/v1/audits/{other["id"]}', headers=_owner(auth_header_factory))
    assert response.status_code == 404
    assert response.json()['detail'] == 'Audit not found'
    listed = client.get(
        '/api/v1/audits',
        headers=_owner(auth_header_factory),
        params={'franchise_id': str(FRANCHISE_B)},
    )
    assert listed.status_code == 200
    assert listed.json()['total'] == 0


def test_changing_setting_does_not_modify_audit_records(client, auth_header_factory, fake_db):
    created = _create(client, _admin(auth_header_factory), franchise_id=str(FRANCHISE_A))
    before_audits = deepcopy(fake_db.tables['franchise_audits'])
    before_items = deepcopy(fake_db.tables['franchise_audit_items'])
    _set_owner_audit(client, auth_header_factory, True)
    _set_owner_audit(client, auth_header_factory, False)
    assert fake_db.tables['franchise_audits'] == before_audits
    assert fake_db.tables['franchise_audit_items'] == before_items
    detail = client.get(f'/api/v1/audits/{created["id"]}', headers=_admin(auth_header_factory))
    assert detail.status_code == 200
    assert detail.json()['id'] == created['id']
    assert detail.json()['franchise_id'] == str(FRANCHISE_A)


def test_client_cannot_update_setting_by_supplying_role_or_franchise(client, auth_header_factory):
    response = client.patch(
        SETTING_PATH,
        headers=_owner(auth_header_factory),
        json={
            'franchise_owner_audit_enabled': True,
            'role': 'SYSTEM_ADMIN',
            'franchise_id': str(FRANCHISE_A),
        },
    )
    assert response.status_code == 403
    current = client.get(SETTING_PATH, headers=_admin(auth_header_factory))
    assert current.json()['franchise_owner_audit_enabled'] is False
