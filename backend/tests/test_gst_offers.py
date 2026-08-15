"""Configurable GST, CGST/SGST split, and basic POS offers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from tests.conftest import (
    ADMIN_ID,
    EMPLOYEE_ID,
    FRANCHISE_A,
    FRANCHISE_B,
    OWNER_CANDIDATE_ID,
    OWNER_ID,
    PRODUCT_ORANGE,
)


def _admin(auth_header_factory):
    return auth_header_factory(ADMIN_ID, 'admin@realstick.in')


def _owner(auth_header_factory):
    return auth_header_factory(OWNER_ID, 'owner@realstick.in')


def _employee(auth_header_factory):
    return auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in')


def _employee_b(auth_header_factory):
    return auth_header_factory(OWNER_CANDIDATE_ID, 'candidate@realstick.in')


def _create_offer(client, auth_header_factory, **overrides):
    payload = {
        'name': 'Summer Special',
        'description': '10% OFF',
        'discount_type': 'PERCENTAGE',
        'discount_value': 10,
        'is_active': True,
    }
    payload.update(overrides)
    return client.post('/api/v1/admin/offers', headers=_admin(auth_header_factory), json=payload)


def _assign_price(client, auth_header_factory, *, selling_price=1000):
    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={
            'product_id': str(PRODUCT_ORANGE),
            'selling_price': selling_price,
            'is_active': True,
        },
    )
    assert response.status_code == 201
    return response.json()


# ── GST admin ───────────────────────────────────────────────────────────────


def test_admin_can_read_gst(client, auth_header_factory):
    response = client.get('/api/v1/admin/gst', headers=_admin(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['rate'] == 5
    assert body['cgst_rate'] == 2.5
    assert body['sgst_rate'] == 2.5


def test_admin_can_update_gst(client, auth_header_factory):
    response = client.patch(
        '/api/v1/admin/gst',
        headers=_admin(auth_header_factory),
        json={'rate': 12, 'cgst_rate': 9, 'sgst_rate': 9},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['rate'] == 12
    assert body['cgst_rate'] == 6
    assert body['sgst_rate'] == 6


def test_owner_cannot_read_or_update_gst(client, auth_header_factory):
    assert client.get('/api/v1/admin/gst', headers=_owner(auth_header_factory)).status_code == 403
    assert client.patch(
        '/api/v1/admin/gst',
        headers=_owner(auth_header_factory),
        json={'rate': 18},
    ).status_code == 403


def test_employee_cannot_read_or_update_gst(client, auth_header_factory):
    assert client.get('/api/v1/admin/gst', headers=_employee(auth_header_factory)).status_code == 403
    assert client.patch(
        '/api/v1/admin/gst',
        headers=_employee(auth_header_factory),
        json={'rate': 18},
    ).status_code == 403


def test_gst_five_percent_splits_evenly(client, auth_header_factory):
    body = client.get('/api/v1/admin/gst', headers=_admin(auth_header_factory)).json()
    assert body['rate'] == 5
    assert body['cgst_rate'] == 2.5
    assert body['sgst_rate'] == 2.5


def test_gst_twelve_percent_splits_evenly(client, auth_header_factory):
    body = client.patch(
        '/api/v1/admin/gst',
        headers=_admin(auth_header_factory),
        json={'rate': 12},
    ).json()
    assert body['cgst_rate'] == 6
    assert body['sgst_rate'] == 6


def test_gst_negative_and_over_max_rejected(client, auth_header_factory):
    assert client.patch(
        '/api/v1/admin/gst',
        headers=_admin(auth_header_factory),
        json={'rate': -1},
    ).status_code == 422
    assert client.patch(
        '/api/v1/admin/gst',
        headers=_admin(auth_header_factory),
        json={'rate': 41},
    ).status_code == 422


def test_gst_uneven_split_rejected(client, auth_header_factory):
    response = client.patch(
        '/api/v1/admin/gst',
        headers=_admin(auth_header_factory),
        json={'rate': 5.01},
    )
    assert response.status_code == 422


# ── Offers admin ────────────────────────────────────────────────────────────


def test_admin_can_create_offer(client, auth_header_factory):
    response = _create_offer(client, auth_header_factory)
    assert response.status_code == 201
    body = response.json()
    assert body['name'] == 'Summer Special'
    assert body['discount_type'] == 'PERCENTAGE'
    assert body['discount_value'] == 10
    assert body['is_active'] is True
    assert body['franchise_id'] is None


def test_admin_can_edit_offer(client, auth_header_factory):
    created = _create_offer(client, auth_header_factory)
    offer_id = created.json()['id']
    response = client.patch(
        f'/api/v1/admin/offers/{offer_id}',
        headers=_admin(auth_header_factory),
        json={'name': 'Weekend Offer', 'discount_value': 15},
    )
    assert response.status_code == 200
    assert response.json()['name'] == 'Weekend Offer'
    assert response.json()['discount_value'] == 15


def test_admin_can_activate_and_deactivate_offer(client, auth_header_factory):
    offer_id = _create_offer(client, auth_header_factory).json()['id']
    deactivated = client.patch(
        f'/api/v1/admin/offers/{offer_id}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()['is_active'] is False
    activated = client.patch(
        f'/api/v1/admin/offers/{offer_id}',
        headers=_admin(auth_header_factory),
        json={'is_active': True},
    )
    assert activated.json()['is_active'] is True


def test_offer_discount_cannot_exceed_100(client, auth_header_factory):
    assert _create_offer(client, auth_header_factory, discount_value=101).status_code == 422
    assert _create_offer(client, auth_header_factory, discount_value=0).status_code == 422
    assert _create_offer(client, auth_header_factory, discount_value=-5).status_code == 422


def test_b2g1_discount_type_rejected(client, auth_header_factory):
    response = _create_offer(client, auth_header_factory, discount_type='B2G1')
    assert response.status_code == 422


def test_owner_cannot_manage_offers(client, auth_header_factory):
    assert client.get('/api/v1/admin/offers', headers=_owner(auth_header_factory)).status_code == 403
    assert client.post(
        '/api/v1/admin/offers',
        headers=_owner(auth_header_factory),
        json={'name': 'Owner Offer', 'discount_value': 10},
    ).status_code == 403


def test_employee_cannot_modify_offers(client, auth_header_factory):
    offer_id = _create_offer(client, auth_header_factory).json()['id']
    assert client.get('/api/v1/admin/offers', headers=_employee(auth_header_factory)).status_code == 403
    assert client.post(
        '/api/v1/admin/offers',
        headers=_employee(auth_header_factory),
        json={'name': 'Staff Hack', 'discount_value': 90},
    ).status_code == 403
    assert client.patch(
        f'/api/v1/admin/offers/{offer_id}',
        headers=_employee(auth_header_factory),
        json={'discount_value': 90, 'is_active': False},
    ).status_code == 403


# ── POS offer visibility ────────────────────────────────────────────────────


def test_active_offer_appears_in_pos(client, auth_header_factory):
    _create_offer(client, auth_header_factory)
    response = client.get('/api/v1/pos/offers', headers=_employee(auth_header_factory))
    assert response.status_code == 200
    names = {item['name'] for item in response.json()['items']}
    assert 'Summer Special' in names


def test_inactive_offer_does_not_appear_in_pos(client, auth_header_factory):
    _create_offer(client, auth_header_factory, name='Staff Offer', is_active=False)
    names = {
        item['name']
        for item in client.get('/api/v1/pos/offers', headers=_employee(auth_header_factory)).json()['items']
    }
    assert 'Staff Offer' not in names


def test_expired_offer_does_not_appear_in_pos(client, auth_header_factory):
    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    earlier = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    _create_offer(
        client,
        auth_header_factory,
        name='Expired Offer',
        valid_from=past,
        valid_to=earlier,
    )
    names = {
        item['name']
        for item in client.get('/api/v1/pos/offers', headers=_employee(auth_header_factory)).json()['items']
    }
    assert 'Expired Offer' not in names


def test_future_offer_does_not_appear_in_pos(client, auth_header_factory):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    _create_offer(client, auth_header_factory, name='Future Offer', valid_from=future)
    names = {
        item['name']
        for item in client.get('/api/v1/pos/offers', headers=_employee(auth_header_factory)).json()['items']
    }
    assert 'Future Offer' not in names


def test_employee_cannot_access_another_franchise_offers(client, auth_header_factory):
    _create_offer(
        client,
        auth_header_factory,
        name='Franchise B Only',
        franchise_id=str(FRANCHISE_B),
    )
    _create_offer(client, auth_header_factory, name='Global Offer')
    names_a = {
        item['name']
        for item in client.get('/api/v1/pos/offers', headers=_employee(auth_header_factory)).json()['items']
    }
    names_b = {
        item['name']
        for item in client.get('/api/v1/pos/offers', headers=_employee_b(auth_header_factory)).json()['items']
    }
    assert 'Franchise B Only' not in names_a
    assert 'Franchise B Only' in names_b
    assert 'Global Offer' in names_a
    assert 'Global Offer' in names_b


def test_admin_and_owner_cannot_list_pos_offers(client, auth_header_factory):
    assert client.get('/api/v1/pos/offers', headers=_admin(auth_header_factory)).status_code == 403
    assert client.get('/api/v1/pos/offers', headers=_owner(auth_header_factory)).status_code == 403


# ── Apply offer / calculation ───────────────────────────────────────────────


def test_employee_can_apply_valid_offer_before_gst(client, auth_header_factory):
    _assign_price(client, auth_header_factory, selling_price=1000)
    offer_id = _create_offer(client, auth_header_factory).json()['id']
    response = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={
            'items': [{'product_id': str(PRODUCT_ORANGE), 'quantity': 1}],
            'payment_method': 'UPI',
            'offer_id': offer_id,
            'discount_percent': 90,
            'discount_amount': 900,
            'gst_amount': 1,
            'total_amount': 1,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body['subtotal'] == 1000
    assert body['discount_amount'] == 100
    assert body['taxable_amount'] == 900
    assert body['cgst_rate'] == 2.5
    assert body['sgst_rate'] == 2.5
    assert body['cgst_amount'] == 22.5
    assert body['sgst_amount'] == 22.5
    assert body['gst_amount'] == 45
    assert body['total_amount'] == 945
    assert body['offer_id'] == offer_id
    assert body['offer_name'] == 'Summer Special'
    assert body['discount_type'] == 'PERCENTAGE'
    assert body['discount_value'] == 10
    assert body['cashier_id'] == str(EMPLOYEE_ID)


def test_no_offer_calculates_gst_on_full_subtotal(client, auth_header_factory):
    _assign_price(client, auth_header_factory, selling_price=1000)
    body = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={
            'items': [{'product_id': str(PRODUCT_ORANGE), 'quantity': 1}],
            'payment_method': 'CASH',
        },
    ).json()
    assert body['subtotal'] == 1000
    assert body['discount_amount'] == 0
    assert body['taxable_amount'] == 1000
    assert body['cgst_amount'] == 25
    assert body['sgst_amount'] == 25
    assert body['gst_amount'] == 50
    assert body['total_amount'] == 1050


def test_only_one_offer_can_be_applied(client, auth_header_factory):
    _assign_price(client, auth_header_factory, selling_price=1000)
    first = _create_offer(client, auth_header_factory, name='Summer Special').json()['id']
    second = _create_offer(client, auth_header_factory, name='Weekend Offer', discount_value=15).json()['id']
    body = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={
            'items': [{'product_id': str(PRODUCT_ORANGE), 'quantity': 1}],
            'payment_method': 'CARD',
            'offer_id': first,
            'offer_ids': [first, second],
        },
    ).json()
    assert body['offer_id'] == first
    assert body['discount_value'] == 10
    assert body['discount_amount'] == 100
    assert body['total_amount'] == 945


def test_full_discount_results_in_zero_taxable_gst_and_total(client, auth_header_factory):
    _assign_price(client, auth_header_factory, selling_price=1000)
    offer_id = _create_offer(client, auth_header_factory, name='Staff Offer', discount_value=100).json()['id']
    body = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={
            'items': [{'product_id': str(PRODUCT_ORANGE), 'quantity': 1}],
            'payment_method': 'UPI',
            'offer_id': offer_id,
        },
    ).json()
    assert body['discount_amount'] == 1000
    assert body['taxable_amount'] == 0
    assert body['cgst_amount'] == 0
    assert body['sgst_amount'] == 0
    assert body['gst_amount'] == 0
    assert body['total_amount'] == 0


def test_inactive_offer_cannot_be_applied(client, auth_header_factory, fake_db):
    _assign_price(client, auth_header_factory, selling_price=1000)
    offer_id = _create_offer(client, auth_header_factory, is_active=False).json()['id']
    before = len(fake_db.tables['orders'])
    response = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={
            'items': [{'product_id': str(PRODUCT_ORANGE), 'quantity': 1}],
            'payment_method': 'UPI',
            'offer_id': offer_id,
        },
    )
    assert response.status_code == 422
    assert len(fake_db.tables['orders']) == before


def test_employee_cannot_apply_other_franchise_offer(client, auth_header_factory, fake_db):
    _assign_price(client, auth_header_factory, selling_price=1000)
    offer_id = _create_offer(
        client,
        auth_header_factory,
        name='Franchise B Only',
        franchise_id=str(FRANCHISE_B),
    ).json()['id']
    before = len(fake_db.tables['orders'])
    response = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={
            'items': [{'product_id': str(PRODUCT_ORANGE), 'quantity': 1}],
            'payment_method': 'UPI',
            'offer_id': offer_id,
        },
    )
    assert response.status_code == 403
    assert len(fake_db.tables['orders']) == before


# ── Snapshots ───────────────────────────────────────────────────────────────


def test_order_snapshots_gst_and_offer_and_survives_admin_changes(client, auth_header_factory, fake_db):
    _assign_price(client, auth_header_factory, selling_price=1000)
    offer_id = _create_offer(client, auth_header_factory).json()['id']
    created = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={
            'items': [{'product_id': str(PRODUCT_ORANGE), 'quantity': 1}],
            'payment_method': 'UPI',
            'offer_id': offer_id,
        },
    )
    assert created.status_code == 201
    order_id = created.json()['id']

    client.patch('/api/v1/admin/gst', headers=_admin(auth_header_factory), json={'rate': 12})
    client.patch(
        f'/api/v1/admin/offers/{offer_id}',
        headers=_admin(auth_header_factory),
        json={'name': 'Changed Name', 'discount_value': 50, 'is_active': False},
    )

    fetched = client.get(f'/api/v1/pos/orders/{order_id}', headers=_employee(auth_header_factory))
    assert fetched.status_code == 200
    body = fetched.json()
    assert body['gst_rate'] == 5
    assert body['cgst_rate'] == 2.5
    assert body['sgst_rate'] == 2.5
    assert body['cgst_amount'] == 22.5
    assert body['sgst_amount'] == 22.5
    assert body['gst_amount'] == 45
    assert body['offer_id'] == offer_id
    assert body['offer_name'] == 'Summer Special'
    assert body['discount_type'] == 'PERCENTAGE'
    assert body['discount_value'] == 10
    assert body['discount_amount'] == 100
    assert body['taxable_amount'] == 900
    assert body['total_amount'] == 945

    # Receipt contract: all thermal-receipt fields are present on the snapshot.
    assert body['offer_name']
    assert 'discount_amount' in body
    assert 'taxable_amount' in body
    assert 'cgst_amount' in body
    assert 'sgst_amount' in body
    assert 'gst_amount' in body
    assert 'total_amount' in body
