"""M11 Franchise Operational Audit — authorization, creation, snapshots, filters."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from app.modules.audits.service import FRANCHISE_OPERATIONAL_CHECKLIST
from app.modules.reports.dates import utc_today
from tests.conftest import ADMIN_ID, EMPLOYEE_ID, FRANCHISE_A, FRANCHISE_B, OWNER_ID

CANONICAL_KEYS = [str(item['item_key']) for item in FRANCHISE_OPERATIONAL_CHECKLIST]


def _admin(auth_header_factory):
    return auth_header_factory(ADMIN_ID, 'admin@realstick.in')


def _owner(auth_header_factory):
    return auth_header_factory(OWNER_ID, 'owner@realstick.in')


def _employee(auth_header_factory):
    return auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in')


def _items(*status_overrides: tuple[str, str], default: str = 'PASS') -> list[dict]:
    statuses = dict(status_overrides)
    return [
        {
            'item_key': key,
            'status': statuses.get(key, default),
            'remarks': f'Remark {key}' if key in statuses else None,
        }
        for key in CANONICAL_KEYS
    ]


def _create_payload(**overrides) -> dict:
    payload = {
        'franchise_id': str(FRANCHISE_A),
        'audit_date': utc_today().isoformat(),
        'remarks': 'General remarks',
        'items': _items(),
    }
    payload.update(overrides)
    return payload


@pytest.fixture(autouse=True)
def enable_franchise_owner_audit(client, auth_header_factory):
    """Audit business-logic tests assume Admin has enabled Franchise Owner access."""
    response = client.patch(
        '/api/v1/admin/settings/franchise-audit',
        headers=_admin(auth_header_factory),
        json={'franchise_owner_audit_enabled': True},
    )
    assert response.status_code == 200, response.text


def _create(client, headers, **overrides) -> dict:
    response = client.post('/api/v1/audits', headers=headers, json=_create_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# ── Authorization ───────────────────────────────────────────────────────────


def test_admin_can_list_audits(client, auth_header_factory):
    created = _create(client, _admin(auth_header_factory))
    response = client.get('/api/v1/audits', headers=_admin(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['page'] == 1
    assert body['page_size'] == 20
    assert body['total'] == 1
    assert body['items'][0]['id'] == created['id']
    assert body['items'][0]['franchise_name'] == 'Hyderabad — Main Store'


def test_admin_can_create_audit(client, auth_header_factory):
    response = client.post(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        json=_create_payload(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body['franchise_id'] == str(FRANCHISE_A)
    assert body['overall_status'] == 'PASS'
    assert len(body['items']) == 10


def test_admin_can_view_any_franchise_audit(client, auth_header_factory):
    other = _create(client, _admin(auth_header_factory), franchise_id=str(FRANCHISE_B))
    response = client.get(f'/api/v1/audits/{other["id"]}', headers=_admin(auth_header_factory))
    assert response.status_code == 200
    assert response.json()['franchise_id'] == str(FRANCHISE_B)
    assert response.json()['franchise_name'] == 'Secunderabad Kiosk'


def test_owner_can_list_own_franchise_audits(client, auth_header_factory):
    created = _create(client, _owner(auth_header_factory), franchise_id=None)
    response = client.get('/api/v1/audits', headers=_owner(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['total'] == 1
    assert body['items'][0]['id'] == created['id']
    assert body['items'][0]['franchise_id'] == str(FRANCHISE_A)


def test_owner_can_create_own_franchise_audit(client, auth_header_factory):
    response = client.post(
        '/api/v1/audits',
        headers=_owner(auth_header_factory),
        json=_create_payload(franchise_id=None),
    )
    assert response.status_code == 201
    assert response.json()['franchise_id'] == str(FRANCHISE_A)


def test_owner_can_view_own_franchise_audit(client, auth_header_factory):
    created = _create(client, _owner(auth_header_factory))
    response = client.get(f'/api/v1/audits/{created["id"]}', headers=_owner(auth_header_factory))
    assert response.status_code == 200
    assert response.json()['id'] == created['id']


def test_owner_cannot_view_another_franchise_audit(client, auth_header_factory):
    other = _create(client, _admin(auth_header_factory), franchise_id=str(FRANCHISE_B))
    response = client.get(f'/api/v1/audits/{other["id"]}', headers=_owner(auth_header_factory))
    assert response.status_code == 404
    assert response.json()['detail'] == 'Audit not found'


def test_owner_list_excludes_other_franchises(client, auth_header_factory):
    own = _create(client, _owner(auth_header_factory))
    _create(client, _admin(auth_header_factory), franchise_id=str(FRANCHISE_B))
    listed = client.get(
        '/api/v1/audits',
        headers=_owner(auth_header_factory),
        params={'franchise_id': str(FRANCHISE_B)},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body['total'] == 1
    assert body['items'][0]['id'] == own['id']
    assert body['items'][0]['franchise_id'] == str(FRANCHISE_A)


def test_employee_get_returns_403(client, auth_header_factory):
    created = _create(client, _admin(auth_header_factory))
    listed = client.get('/api/v1/audits', headers=_employee(auth_header_factory))
    assert listed.status_code == 403
    detail = client.get(f'/api/v1/audits/{created["id"]}', headers=_employee(auth_header_factory))
    assert detail.status_code == 403


def test_employee_post_returns_403(client, auth_header_factory):
    response = client.post(
        '/api/v1/audits',
        headers=_employee(auth_header_factory),
        json=_create_payload(),
    )
    assert response.status_code == 403


def test_unauthenticated_returns_401(client):
    assert client.get('/api/v1/audits').status_code == 401
    assert client.post('/api/v1/audits', json=_create_payload()).status_code == 401
    assert client.get(f'/api/v1/audits/{uuid4()}').status_code == 401


# ── Creation ────────────────────────────────────────────────────────────────


def test_valid_10_item_audit_returns_201(client, auth_header_factory):
    response = client.post(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        json=_create_payload(),
    )
    assert response.status_code == 201
    body = response.json()
    assert {item['item_key'] for item in body['items']} == set(CANONICAL_KEYS)
    assert [item['display_order'] for item in body['items']] == list(range(1, 11))


def test_admin_missing_franchise_returns_422(client, auth_header_factory):
    response = client.post(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        json=_create_payload(franchise_id=None),
    )
    assert response.status_code == 422


def test_unknown_franchise_returns_404(client, auth_header_factory):
    response = client.post(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        json=_create_payload(franchise_id=str(uuid4())),
    )
    assert response.status_code == 404
    assert response.json()['detail'] == 'Franchise not found'


def test_owner_client_franchise_id_is_ignored(client, auth_header_factory):
    response = client.post(
        '/api/v1/audits',
        headers=_owner(auth_header_factory),
        json=_create_payload(franchise_id=str(FRANCHISE_B)),
    )
    assert response.status_code == 201
    body = response.json()
    assert body['franchise_id'] == str(FRANCHISE_A)
    assert body['franchise_name'] == 'Hyderabad — Main Store'


def test_invalid_audit_date_returns_422(client, auth_header_factory):
    payload = _create_payload()
    payload['audit_date'] = 'not-a-date'
    response = client.post('/api/v1/audits', headers=_admin(auth_header_factory), json=payload)
    assert response.status_code == 422


def test_future_audit_date_returns_422(client, auth_header_factory):
    future = (utc_today() + timedelta(days=1)).isoformat()
    response = client.post(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        json=_create_payload(audit_date=future),
    )
    assert response.status_code == 422


def test_missing_checklist_item_returns_422(client, auth_header_factory):
    items = _items()[:-1]
    response = client.post(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        json=_create_payload(items=items),
    )
    assert response.status_code == 422


def test_extra_checklist_item_returns_422(client, auth_header_factory):
    items = _items() + [{'item_key': 'unknown_item', 'status': 'PASS'}]
    response = client.post(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        json=_create_payload(items=items),
    )
    assert response.status_code == 422


def test_duplicate_item_key_returns_422(client, auth_header_factory):
    items = _items()
    items[1]['item_key'] = items[0]['item_key']
    response = client.post(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        json=_create_payload(items=items),
    )
    assert response.status_code == 422


def test_invalid_status_returns_422(client, auth_header_factory):
    items = _items()
    items[0]['status'] = 'INVALID'
    response = client.post(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        json=_create_payload(items=items),
    )
    assert response.status_code == 422


# ── Overall status ──────────────────────────────────────────────────────────


def test_all_pass_overall_status_is_pass(client, auth_header_factory):
    body = _create(client, _admin(auth_header_factory), items=_items())
    assert body['overall_status'] == 'PASS'


def test_pass_plus_needs_attention_overall_status(client, auth_header_factory):
    body = _create(
        client,
        _admin(auth_header_factory),
        items=_items(('pos_working', 'NEEDS_ATTENTION')),
    )
    assert body['overall_status'] == 'NEEDS_ATTENTION'


def test_pass_plus_fail_overall_status_is_fail(client, auth_header_factory):
    body = _create(
        client,
        _admin(auth_header_factory),
        items=_items(('internet_working', 'FAIL')),
    )
    assert body['overall_status'] == 'FAIL'


def test_needs_attention_plus_fail_overall_status_is_fail(client, auth_header_factory):
    body = _create(
        client,
        _admin(auth_header_factory),
        items=_items(('pos_working', 'NEEDS_ATTENTION'), ('billing_process_working', 'FAIL')),
    )
    assert body['overall_status'] == 'FAIL'


# ── Identity ────────────────────────────────────────────────────────────────


def test_auditor_id_comes_from_authenticated_profile(client, auth_header_factory):
    body = _create(client, _admin(auth_header_factory))
    assert body['auditor_id'] == str(ADMIN_ID)


def test_auditor_name_snapshot_comes_from_authenticated_profile(client, auth_header_factory):
    body = _create(client, _admin(auth_header_factory))
    assert body['auditor_name'] == 'System Admin'
    owner = _create(client, _owner(auth_header_factory))
    assert owner['auditor_id'] == str(OWNER_ID)
    assert owner['auditor_name'] == 'Franchise Owner'


def test_client_cannot_control_auditor_id(client, auth_header_factory):
    payload = _create_payload()
    payload['auditor_id'] = str(OWNER_ID)
    payload['auditor_name_snapshot'] = 'Hacked Name'
    payload['overall_status'] = 'FAIL'
    response = client.post('/api/v1/audits', headers=_admin(auth_header_factory), json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body['auditor_id'] == str(ADMIN_ID)
    assert body['auditor_name'] == 'System Admin'
    assert body['overall_status'] == 'PASS'


# ── Historical snapshots ────────────────────────────────────────────────────


def test_franchise_name_snapshot_survives_rename(client, auth_header_factory, fake_db):
    created = _create(client, _admin(auth_header_factory))
    for row in fake_db.tables['franchises']:
        if row['id'] == str(FRANCHISE_A):
            row['name'] = 'Franchise 1 - Hyderabad'
    detail = client.get(f'/api/v1/audits/{created["id"]}', headers=_admin(auth_header_factory))
    assert detail.status_code == 200
    assert detail.json()['franchise_name'] == 'Hyderabad — Main Store'
    listed = client.get('/api/v1/audits', headers=_admin(auth_header_factory))
    assert listed.json()['items'][0]['franchise_name'] == 'Hyderabad — Main Store'


def test_auditor_name_snapshot_survives_profile_rename(client, auth_header_factory, fake_db):
    created = _create(client, _admin(auth_header_factory))
    for row in fake_db.tables['profiles']:
        if row['id'] == str(ADMIN_ID):
            row['full_name'] = 'Renamed Admin'
    detail = client.get(f'/api/v1/audits/{created["id"]}', headers=_admin(auth_header_factory))
    assert detail.status_code == 200
    assert detail.json()['auditor_name'] == 'System Admin'


def test_checklist_item_snapshot_remains_unchanged(client, auth_header_factory):
    created = _create(client, _admin(auth_header_factory))
    labels = {item['item_key']: item['checklist_item'] for item in created['items']}
    expected = {str(item['item_key']): str(item['label']) for item in FRANCHISE_OPERATIONAL_CHECKLIST}
    assert labels == expected
    detail = client.get(f'/api/v1/audits/{created["id"]}', headers=_admin(auth_header_factory))
    again = {item['item_key']: item['checklist_item'] for item in detail.json()['items']}
    assert again == expected


def test_stored_item_status_remains_unchanged(client, auth_header_factory):
    created = _create(
        client,
        _admin(auth_header_factory),
        items=_items(('pos_working', 'FAIL'), ('internet_working', 'NEEDS_ATTENTION')),
    )
    detail = client.get(f'/api/v1/audits/{created["id"]}', headers=_admin(auth_header_factory))
    statuses = {item['item_key']: item['status'] for item in detail.json()['items']}
    assert statuses['pos_working'] == 'FAIL'
    assert statuses['internet_working'] == 'NEEDS_ATTENTION'
    assert detail.json()['overall_status'] == 'FAIL'


# ── Filtering / pagination ──────────────────────────────────────────────────


def test_admin_franchise_filter(client, auth_header_factory):
    a = _create(client, _admin(auth_header_factory), franchise_id=str(FRANCHISE_A))
    _create(client, _admin(auth_header_factory), franchise_id=str(FRANCHISE_B))
    listed = client.get(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        params={'franchise_id': str(FRANCHISE_A)},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body['total'] == 1
    assert body['items'][0]['id'] == a['id']


def test_date_range_filter(client, auth_header_factory):
    today = utc_today()
    older = _create(
        client,
        _admin(auth_header_factory),
        audit_date=(today - timedelta(days=10)).isoformat(),
    )
    recent = _create(
        client,
        _admin(auth_header_factory),
        audit_date=(today - timedelta(days=1)).isoformat(),
    )
    listed = client.get(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        params={
            'from_date': (today - timedelta(days=2)).isoformat(),
            'to_date': today.isoformat(),
        },
    )
    assert listed.status_code == 200
    ids = {item['id'] for item in listed.json()['items']}
    assert recent['id'] in ids
    assert older['id'] not in ids


def test_overall_status_filter(client, auth_header_factory):
    _create(client, _admin(auth_header_factory), items=_items())
    failed = _create(
        client,
        _admin(auth_header_factory),
        items=_items(('pos_working', 'FAIL')),
    )
    listed = client.get(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        params={'overall_status': 'FAIL'},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body['total'] == 1
    assert body['items'][0]['id'] == failed['id']
    assert body['items'][0]['overall_status'] == 'FAIL'


def test_pagination(client, auth_header_factory):
    today = utc_today()
    first = _create(
        client,
        _admin(auth_header_factory),
        audit_date=(today - timedelta(days=2)).isoformat(),
    )
    second = _create(
        client,
        _admin(auth_header_factory),
        audit_date=(today - timedelta(days=1)).isoformat(),
    )
    third = _create(client, _admin(auth_header_factory), audit_date=today.isoformat())

    page1 = client.get(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        params={'page': 1, 'page_size': 2},
    )
    assert page1.status_code == 200
    body1 = page1.json()
    assert body1['page'] == 1
    assert body1['page_size'] == 2
    assert body1['total'] == 3
    assert len(body1['items']) == 2
    assert {item['id'] for item in body1['items']} == {third['id'], second['id']}

    page2 = client.get(
        '/api/v1/audits',
        headers=_admin(auth_header_factory),
        params={'page': 2, 'page_size': 2},
    )
    assert page2.status_code == 200
    body2 = page2.json()
    assert body2['total'] == 3
    assert [item['id'] for item in body2['items']] == [first['id']]


# ── Detail ──────────────────────────────────────────────────────────────────


def test_items_returned_in_display_order(client, auth_header_factory):
    reversed_items = list(reversed(_items()))
    created = _create(client, _admin(auth_header_factory), items=reversed_items)
    assert [item['display_order'] for item in created['items']] == list(range(1, 11))
    assert [item['item_key'] for item in created['items']] == CANONICAL_KEYS
    detail = client.get(f'/api/v1/audits/{created["id"]}', headers=_admin(auth_header_factory))
    assert [item['item_key'] for item in detail.json()['items']] == CANONICAL_KEYS


def test_completed_audits_have_no_patch_or_delete(client, auth_header_factory):
    created = _create(client, _admin(auth_header_factory))
    patched = client.patch(
        f'/api/v1/audits/{created["id"]}',
        headers=_admin(auth_header_factory),
        json={'remarks': 'changed'},
    )
    deleted = client.delete(
        f'/api/v1/audits/{created["id"]}',
        headers=_admin(auth_header_factory),
    )
    assert patched.status_code == 405
    assert deleted.status_code == 405
    still = client.get(f'/api/v1/audits/{created["id"]}', headers=_admin(auth_header_factory))
    assert still.status_code == 200
    assert still.json()['remarks'] == 'General remarks'
