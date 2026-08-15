"""M7 completed bills / order history — read-only APIs and franchise isolation."""

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
    PRODUCT_NIMBU,
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


def _checkout(client, headers, **overrides):
    payload = {
        'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 2}],
        'payment_method': 'UPI',
    }
    payload.update(overrides)
    return client.post('/api/v1/pos/orders', headers=headers, json=payload)


def _assign_nimbu_b(client, auth_header_factory, *, selling_price=22):
    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
        json={
            'product_id': str(PRODUCT_NIMBU),
            'selling_price': selling_price,
            'is_active': True,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_offer(client, auth_header_factory, **overrides):
    payload = {
        'name': 'Summer Special',
        'description': '10% OFF',
        'discount_type': 'PERCENTAGE',
        'discount_value': 10,
        'is_active': True,
    }
    payload.update(overrides)
    response = client.post('/api/v1/admin/offers', headers=_admin(auth_header_factory), json=payload)
    assert response.status_code == 201
    return response.json()


def _ids(body: dict) -> set[str]:
    return {item['id'] for item in body['items']}


# ── List authorization / franchise isolation ────────────────────────────────


def test_unauthenticated_orders_are_rejected(client):
    assert client.get('/api/v1/orders').status_code == 401
    assert client.get(f'/api/v1/orders/{uuid4()}').status_code == 401


def test_employee_can_list_completed_bills_for_own_franchise(client, auth_header_factory):
    created = _checkout(client, _employee(auth_header_factory))
    assert created.status_code == 201
    response = client.get('/api/v1/orders', headers=_employee(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['page'] == 1
    assert body['page_size'] == 20
    assert body['total'] == 1
    assert len(body['items']) == 1
    row = body['items'][0]
    assert row['id'] == created.json()['id']
    assert row['bill_number'] == created.json()['bill_number']
    assert row['franchise_id'] == str(FRANCHISE_A)
    assert row['cashier_id'] == str(EMPLOYEE_ID)
    assert row['cashier_name'] == 'Employee User'
    assert row['payment_method'] == 'UPI'
    assert row['total_amount'] == created.json()['total_amount']
    assert 'items' not in row
    assert 'product_name_snapshot' not in row


def test_employee_cannot_see_another_franchise_bills(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory))
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='CASH')
    assert other.status_code == 201

    listed = client.get('/api/v1/orders', headers=_employee(auth_header_factory)).json()
    assert listed['total'] == 1
    assert listed['items'][0]['id'] == own.json()['id']
    assert listed['items'][0]['franchise_id'] == str(FRANCHISE_A)

    hidden = client.get(
        f'/api/v1/orders/{other.json()["id"]}',
        headers=_employee(auth_header_factory),
    )
    assert hidden.status_code == 404
    assert hidden.json()['detail'] == 'Order not found'


def test_employee_supplied_franchise_id_is_ignored(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory))
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory))
    assert other.status_code == 201

    listed = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'franchise_id': str(FRANCHISE_B)},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body['total'] == 1
    assert body['items'][0]['franchise_id'] == str(FRANCHISE_A)


def test_owner_can_list_own_franchise_bills(client, auth_header_factory):
    created = _checkout(client, _employee(auth_header_factory), payment_method='CARD')
    assert created.status_code == 201
    response = client.get('/api/v1/orders', headers=_owner(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['total'] == 1
    assert body['items'][0]['id'] == created.json()['id']
    assert body['items'][0]['franchise_id'] == str(FRANCHISE_A)
    assert body['items'][0]['cashier_name'] == 'Employee User'


def test_owner_cannot_see_another_franchise_bills(client, auth_header_factory):
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory))
    assert other.status_code == 201
    listed = client.get('/api/v1/orders', headers=_owner(auth_header_factory)).json()
    assert listed['total'] == 0
    assert listed['items'] == []
    hidden = client.get(
        f'/api/v1/orders/{other.json()["id"]}',
        headers=_owner(auth_header_factory),
    )
    assert hidden.status_code == 404


def test_admin_can_list_selected_franchise_bills(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory))
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='CASH')
    assert other.status_code == 201

    listed = client.get(
        '/api/v1/orders',
        headers=_admin(auth_header_factory),
        params={'franchise_id': str(FRANCHISE_A)},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body['total'] == 1
    assert body['items'][0]['id'] == own.json()['id']
    assert body['items'][0]['franchise_name'] == 'Hyderabad — Main Store'


def test_admin_can_retrieve_bill_from_selected_franchise(client, auth_header_factory):
    created = _checkout(client, _employee(auth_header_factory))
    assert created.status_code == 201
    order_id = created.json()['id']
    detail = client.get(f'/api/v1/orders/{order_id}', headers=_admin(auth_header_factory))
    assert detail.status_code == 200
    body = detail.json()
    assert body['id'] == order_id
    assert body['franchise_id'] == str(FRANCHISE_A)
    assert body['status'] == 'COMPLETED'
    assert body['items']


def test_admin_cannot_accidentally_bypass_franchise_filtering(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory))
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory))
    assert other.status_code == 201

    filtered = client.get(
        '/api/v1/orders',
        headers=_admin(auth_header_factory),
        params={'franchise_id': str(FRANCHISE_A)},
    ).json()
    assert _ids(filtered) == {own.json()['id']}
    assert all(item['franchise_id'] == str(FRANCHISE_A) for item in filtered['items'])

    all_franchises = client.get('/api/v1/orders', headers=_admin(auth_header_factory)).json()
    assert all_franchises['total'] == 2
    names = {item['franchise_id']: item['franchise_name'] for item in all_franchises['items']}
    assert names[str(FRANCHISE_A)] == 'Hyderabad — Main Store'
    assert names[str(FRANCHISE_B)] == 'Secunderabad Kiosk'


def test_only_completed_orders_appear(client, auth_header_factory, fake_db):
    completed = _checkout(client, _employee(auth_header_factory))
    assert completed.status_code == 201
    now = datetime.now(timezone.utc).isoformat()
    fake_db.tables['orders'].append(
        {
            'id': str(uuid4()),
            'franchise_id': str(FRANCHISE_A),
            'bill_number': 'RS-DRAFT',
            'status': 'DRAFT',
            'customer_phone': None,
            'subtotal': 22,
            'discount_amount': 0,
            'taxable_amount': 22,
            'gst_rate': 5,
            'gst_amount': 1.1,
            'total_amount': 23.1,
            'payment_method': None,
            'cashier_id': str(EMPLOYEE_ID),
            'completed_at': None,
            'cancelled_at': None,
            'created_at': now,
            'updated_at': now,
        }
    )
    cancelled_id = str(uuid4())
    fake_db.tables['orders'].append(
        {
            'id': cancelled_id,
            'franchise_id': str(FRANCHISE_A),
            'bill_number': 'RS-CANCEL',
            'status': 'CANCELLED',
            'customer_phone': None,
            'subtotal': 22,
            'discount_amount': 0,
            'taxable_amount': 22,
            'gst_rate': 5,
            'gst_amount': 1.1,
            'total_amount': 23.1,
            'payment_method': 'UPI',
            'cashier_id': str(EMPLOYEE_ID),
            'completed_at': None,
            'cancelled_at': now,
            'created_at': now,
            'updated_at': now,
        }
    )

    listed = client.get('/api/v1/orders', headers=_employee(auth_header_factory)).json()
    bills = {item['bill_number'] for item in listed['items']}
    assert completed.json()['bill_number'] in bills
    assert 'RS-DRAFT' not in bills
    assert 'RS-CANCEL' not in bills

    assert client.get(
        f'/api/v1/orders/{cancelled_id}',
        headers=_employee(auth_header_factory),
    ).status_code == 404


# ── Search / filters / pagination ───────────────────────────────────────────


def test_bill_number_search(client, auth_header_factory):
    first = _checkout(client, _employee(auth_header_factory))
    second = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert first.status_code == 201
    assert second.status_code == 201
    bill = first.json()['bill_number']

    found = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'bill_number': bill},
    )
    assert found.status_code == 200
    body = found.json()
    assert body['total'] == 1
    assert body['items'][0]['id'] == first.json()['id']

    case = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'bill_number': bill.lower()},
    )
    assert case.json()['total'] == 1

    missing = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'bill_number': 'RS-9999'},
    )
    assert missing.json()['total'] == 0
    assert missing.json()['items'] == []


def test_bill_number_search_respects_franchise_isolation(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory))
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory))
    assert other.status_code == 201
    assert own.json()['bill_number'] == other.json()['bill_number'] == 'RS-0001'

    found = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'bill_number': 'RS-0001'},
    ).json()
    assert found['total'] == 1
    assert found['items'][0]['id'] == own.json()['id']


def test_date_filtering(client, auth_header_factory, fake_db):
    created = _checkout(client, _employee(auth_header_factory))
    assert created.status_code == 201
    order_id = created.json()['id']
    day = created.json()['completed_at'][:10]

    today = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'from_date': day, 'to_date': day},
    )
    assert today.status_code == 200
    assert _ids(today.json()) == {order_id}

    old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    row = next(item for item in fake_db.tables['orders'] if item['id'] == order_id)
    row['completed_at'] = old
    row['created_at'] = old

    excluded = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'from_date': day, 'to_date': day},
    )
    assert excluded.json()['total'] == 0

    last_30_start = (datetime.now(timezone.utc) - timedelta(days=29)).date().isoformat()
    last_30 = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'from_date': last_30_start, 'to_date': day},
    )
    assert last_30.json()['total'] == 0

    wide_start = (datetime.now(timezone.utc) - timedelta(days=45)).date().isoformat()
    included = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'from_date': wide_start, 'to_date': day},
    )
    assert _ids(included.json()) == {order_id}


def test_invalid_date_range_rejected(client, auth_header_factory):
    response = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'from_date': '2026-08-14', 'to_date': '2026-08-01'},
    )
    assert response.status_code == 422


def test_payment_method_filtering(client, auth_header_factory):
    cash = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    upi = _checkout(client, _employee(auth_header_factory), payment_method='UPI')
    card = _checkout(client, _employee(auth_header_factory), payment_method='CARD')
    assert cash.status_code == upi.status_code == card.status_code == 201

    filtered = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'payment_method': 'CASH'},
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert body['total'] == 1
    assert body['items'][0]['id'] == cash.json()['id']
    assert body['items'][0]['payment_method'] == 'CASH'

    all_methods = client.get('/api/v1/orders', headers=_employee(auth_header_factory)).json()
    assert all_methods['total'] == 3


def test_pagination(client, auth_header_factory):
    created_ids = []
    for index in range(21):
        method = ('CASH', 'UPI', 'CARD')[index % 3]
        response = _checkout(client, _employee(auth_header_factory), payment_method=method)
        assert response.status_code == 201
        created_ids.append(response.json()['id'])

    page1 = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'page': 1, 'page_size': 20},
    )
    assert page1.status_code == 200
    body1 = page1.json()
    assert body1['page'] == 1
    assert body1['page_size'] == 20
    assert body1['total'] == 21
    assert len(body1['items']) == 20

    page2 = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'page': 2, 'page_size': 20},
    ).json()
    assert page2['page'] == 2
    assert page2['total'] == 21
    assert len(page2['items']) == 1
    assert _ids(body1).isdisjoint(_ids(page2))
    assert _ids(body1) | _ids(page2) == set(created_ids)


def test_page_size_is_capped(client, auth_header_factory):
    response = client.get(
        '/api/v1/orders',
        headers=_employee(auth_header_factory),
        params={'page_size': 101},
    )
    assert response.status_code == 422


# ── Detail snapshots ────────────────────────────────────────────────────────


def test_bill_detail_contains_order_snapshots(client, auth_header_factory):
    created = _checkout(
        client,
        _employee(auth_header_factory),
        payment_method='CARD',
        customer_phone='9876543210',
    )
    assert created.status_code == 201
    order_id = created.json()['id']
    detail = client.get(f'/api/v1/orders/{order_id}', headers=_employee(auth_header_factory))
    assert detail.status_code == 200
    body = detail.json()
    assert body['bill_number'] == created.json()['bill_number']
    assert body['status'] == 'COMPLETED'
    assert body['payment_status'] == 'PAID'
    assert body['payment_method'] == 'CARD'
    assert body['customer_phone'] == '9876543210'
    assert body['cashier_name'] == 'Employee User'
    assert body['franchise_name'] == 'Hyderabad — Main Store'
    assert len(body['items']) == 1
    item = body['items'][0]
    assert item['product_name_snapshot'] == 'Nimbu Pudina'
    assert item['unit_price'] == 22
    assert item['quantity'] == 2
    assert item['line_total'] == 44


def test_historical_gst_cgst_sgst_offer_and_product_snapshots(client, auth_header_factory):
    offer = _create_offer(client, auth_header_factory)
    created = _checkout(
        client,
        _employee(auth_header_factory),
        items=[{'product_id': str(PRODUCT_NIMBU), 'quantity': 2}],
        payment_method='UPI',
        offer_id=offer['id'],
    )
    assert created.status_code == 201
    order_id = created.json()['id']
    original = created.json()

    client.patch('/api/v1/admin/gst', headers=_admin(auth_header_factory), json={'rate': 12})
    client.patch(
        f'/api/v1/admin/offers/{offer["id"]}',
        headers=_admin(auth_header_factory),
        json={'name': 'Changed Name', 'discount_value': 50, 'is_active': False},
    )
    renamed = client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'name': 'Nimbu Pudina Deluxe', 'price': 500},
    )
    assert renamed.status_code == 200
    client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'selling_price': 40},
    )

    detail = client.get(f'/api/v1/orders/{order_id}', headers=_owner(auth_header_factory))
    assert detail.status_code == 200
    body = detail.json()
    assert body['gst_rate'] == original['gst_rate'] == 5
    assert body['cgst_rate'] == original['cgst_rate'] == 2.5
    assert body['sgst_rate'] == original['sgst_rate'] == 2.5
    assert body['cgst_amount'] == original['cgst_amount']
    assert body['sgst_amount'] == original['sgst_amount']
    assert body['gst_amount'] == original['gst_amount']
    assert body['offer_name'] == 'Summer Special'
    assert body['discount_value'] == 10
    assert body['discount_amount'] == original['discount_amount']
    assert body['taxable_amount'] == original['taxable_amount']
    assert body['total_amount'] == original['total_amount']
    assert body['items'][0]['product_name_snapshot'] == 'Nimbu Pudina'
    assert body['items'][0]['unit_price'] == 22


# ── Reprint is read-only ────────────────────────────────────────────────────


def test_reprint_uses_existing_order_id_and_does_not_create_another_order(
    client,
    auth_header_factory,
    fake_db,
):
    created = _checkout(client, _employee(auth_header_factory))
    assert created.status_code == 201
    order_id = created.json()['id']
    bill = created.json()['bill_number']
    before_orders = len(fake_db.tables['orders'])
    before_items = len(fake_db.tables['order_items'])
    before_bills = {row['bill_number'] for row in fake_db.tables['orders']}

    first = client.get(f'/api/v1/orders/{order_id}', headers=_employee(auth_header_factory))
    second = client.get(f'/api/v1/orders/{order_id}', headers=_owner(auth_header_factory))
    third = client.get(f'/api/v1/orders/{order_id}', headers=_admin(auth_header_factory))
    assert first.status_code == second.status_code == third.status_code == 200
    assert first.json()['id'] == second.json()['id'] == third.json()['id'] == order_id
    assert first.json()['bill_number'] == second.json()['bill_number'] == bill
    assert len(fake_db.tables['orders']) == before_orders == 1
    assert len(fake_db.tables['order_items']) == before_items
    assert {row['bill_number'] for row in fake_db.tables['orders']} == before_bills


# ── Mutations are not allowed on history APIs ───────────────────────────────


def test_employee_cannot_modify_an_order_through_history_api(client, auth_header_factory, fake_db):
    created = _checkout(client, _employee(auth_header_factory))
    order_id = created.json()['id']
    headers = _employee(auth_header_factory)
    assert client.patch(f'/api/v1/orders/{order_id}', headers=headers, json={'total_amount': 1}).status_code == 405
    assert client.put(f'/api/v1/orders/{order_id}', headers=headers, json={'total_amount': 1}).status_code == 405
    assert client.delete(f'/api/v1/orders/{order_id}', headers=headers).status_code == 405
    assert client.post('/api/v1/orders', headers=headers, json={'payment_method': 'CASH'}).status_code == 405
    assert len(fake_db.tables['orders']) == 1
    assert fake_db.tables['orders'][0]['total_amount'] == created.json()['total_amount']


def test_owner_cannot_modify_an_order(client, auth_header_factory, fake_db):
    created = _checkout(client, _employee(auth_header_factory))
    order_id = created.json()['id']
    headers = _owner(auth_header_factory)
    assert client.patch(f'/api/v1/orders/{order_id}', headers=headers, json={'payment_method': 'CASH'}).status_code == 405
    assert client.delete(f'/api/v1/orders/{order_id}', headers=headers).status_code == 405
    assert client.post('/api/v1/pos/orders', headers=headers, json={
        'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 1}],
        'payment_method': 'UPI',
    }).status_code == 403
    assert len(fake_db.tables['orders']) == 1


def test_admin_cannot_modify_a_completed_order(client, auth_header_factory, fake_db):
    created = _checkout(client, _employee(auth_header_factory))
    order_id = created.json()['id']
    headers = _admin(auth_header_factory)
    assert client.patch(f'/api/v1/orders/{order_id}', headers=headers, json={'total_amount': 1}).status_code == 405
    assert client.delete(f'/api/v1/orders/{order_id}', headers=headers).status_code == 405
    assert client.post('/api/v1/pos/orders', headers=headers, json={
        'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 1}],
        'payment_method': 'UPI',
    }).status_code == 403
    assert len(fake_db.tables['orders']) == 1
    assert client.get(f'/api/v1/pos/orders/{order_id}', headers=headers).status_code == 403


def test_existing_pos_checkout_and_employee_only_authorization_remain(client, auth_header_factory):
    employee = _checkout(client, _employee(auth_header_factory))
    assert employee.status_code == 201
    assert employee.json()['status'] == 'COMPLETED'
    assert employee.json()['bill_number'] == 'RS-0001'

    assert _checkout(client, _owner(auth_header_factory)).status_code == 403
    assert _checkout(client, _admin(auth_header_factory)).status_code == 403
    assert client.get('/api/v1/pos/menu', headers=_owner(auth_header_factory)).status_code == 403
    assert client.get('/api/v1/pos/menu', headers=_admin(auth_header_factory)).status_code == 403

    fetched = client.get(
        f'/api/v1/pos/orders/{employee.json()["id"]}',
        headers=_employee(auth_header_factory),
    )
    assert fetched.status_code == 200
    assert fetched.json()['id'] == employee.json()['id']
