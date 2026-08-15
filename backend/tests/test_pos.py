"""M6 POS / Billing tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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


def _checkout_payload(**overrides):
    payload = {
        'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 2}],
        'payment_method': 'UPI',
    }
    payload.update(overrides)
    return payload


def _complete(client, headers, **overrides):
    return client.post('/api/v1/pos/orders', headers=headers, json=_checkout_payload(**overrides))


def _assign_orange(client, auth_header_factory, *, franchise_id=FRANCHISE_A, selling_price=45, is_active=True):
    response = client.post(
        f'/api/v1/admin/franchises/{franchise_id}/products',
        headers=_admin(auth_header_factory),
        json={
            'product_id': str(PRODUCT_ORANGE),
            'selling_price': selling_price,
            'is_active': is_active,
        },
    )
    assert response.status_code == 201
    return response.json()


# ── Authorization ───────────────────────────────────────────────────────────


def test_employee_can_access_own_franchise_pos_menu(client, auth_header_factory):
    response = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['franchise_id'] == str(FRANCHISE_A)
    assert body['gst_rate'] == 5
    assert body['cgst_rate'] == 2.5
    assert body['sgst_rate'] == 2.5
    ids = {item['product_id'] for item in body['items']}
    assert str(PRODUCT_NIMBU) in ids
    assert str(PRODUCT_ORANGE) not in ids


def test_owner_cannot_access_pos_menu(client, auth_header_factory):
    response = client.get('/api/v1/pos/menu', headers=_owner(auth_header_factory))
    assert response.status_code == 403


def test_owner_cannot_create_pos_order(client, auth_header_factory):
    response = _complete(client, _owner(auth_header_factory))
    assert response.status_code == 403


def test_owner_cannot_get_pos_order(client, auth_header_factory):
    created = _complete(client, _employee(auth_header_factory))
    assert created.status_code == 201
    response = client.get(
        f'/api/v1/pos/orders/{created.json()["id"]}',
        headers=_owner(auth_header_factory),
    )
    assert response.status_code == 403


def test_admin_cannot_access_pos_menu(client, auth_header_factory):
    response = client.get('/api/v1/pos/menu', headers=_admin(auth_header_factory))
    assert response.status_code == 403


def test_admin_cannot_create_pos_order(client, auth_header_factory):
    response = _complete(client, _admin(auth_header_factory))
    assert response.status_code == 403


def test_admin_cannot_get_pos_order(client, auth_header_factory, fake_db):
    created = _complete(client, _employee(auth_header_factory))
    assert created.status_code == 201
    response = client.get(
        f'/api/v1/pos/orders/{created.json()["id"]}',
        headers=_admin(auth_header_factory),
    )
    assert response.status_code == 403


def test_employee_cannot_specify_franchise_id(client, auth_header_factory):
    response = _complete(
        client,
        _employee(auth_header_factory),
        franchise_id=str(FRANCHISE_B),
    )
    assert response.status_code == 201
    body = response.json()
    assert body['franchise_id'] == str(FRANCHISE_A)


def test_employee_cannot_access_another_franchise_order(client, auth_header_factory):
    created = _complete(client, _employee(auth_header_factory))
    assert created.status_code == 201
    response = client.get(
        f'/api/v1/pos/orders/{created.json()["id"]}',
        headers=_employee_b(auth_header_factory),
    )
    assert response.status_code == 404


def test_employee_can_create_pos_order(client, auth_header_factory):
    response = _complete(client, _employee(auth_header_factory))
    assert response.status_code == 201
    body = response.json()
    assert body['franchise_id'] == str(FRANCHISE_A)
    assert body['cashier_id'] == str(EMPLOYEE_ID)
    assert body['status'] == 'COMPLETED'


def test_employee_can_retrieve_own_franchise_order(client, auth_header_factory):
    created = _complete(client, _employee(auth_header_factory))
    assert created.status_code == 201
    order_id = created.json()['id']
    fetched = client.get(f'/api/v1/pos/orders/{order_id}', headers=_employee(auth_header_factory))
    assert fetched.status_code == 200
    assert fetched.json()['id'] == order_id
    assert fetched.json()['franchise_id'] == str(FRANCHISE_A)
    assert client.get('/api/v1/pos/menu').status_code == 401
    assert client.post('/api/v1/pos/orders', json=_checkout_payload()).status_code == 401


# ── Product validation / pricing ────────────────────────────────────────────


def test_menu_uses_franchise_selling_price_not_master(client, auth_header_factory):
    item = next(
        i
        for i in client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory)).json()['items']
        if i['product_id'] == str(PRODUCT_NIMBU)
    )
    assert item['selling_price'] == 22
    assert item['available_for_pos'] is True
    assert 'master_price' not in item
    assert 'price' not in item


def test_assigned_active_product_can_be_sold(client, auth_header_factory):
    response = _complete(client, _employee(auth_header_factory), items=[
        {'product_id': str(PRODUCT_NIMBU), 'quantity': 1},
    ])
    assert response.status_code == 201
    body = response.json()
    assert body['status'] == 'COMPLETED'
    assert body['items'][0]['unit_price'] == 22
    assert body['items'][0]['product_name_snapshot'] == 'Nimbu Pudina'
    assert body['items'][0]['quantity'] == 1
    assert body['items'][0]['line_total'] == 22


def test_unassigned_product_rejected(client, auth_header_factory, fake_db):
    before = len(fake_db.tables['orders'])
    response = _complete(client, _employee(auth_header_factory), items=[
        {'product_id': str(PRODUCT_ORANGE), 'quantity': 1},
    ])
    assert response.status_code == 400
    assert 'not assigned' in response.json()['detail'].lower()
    assert len(fake_db.tables['orders']) == before


def test_inactive_product_rejected(client, auth_header_factory):
    hidden = client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert hidden.status_code == 200
    response = _complete(client, _employee(auth_header_factory))
    assert response.status_code == 400
    assert 'not available' in response.json()['detail'].lower()


def test_inactive_franchise_assignment_rejected(client, auth_header_factory):
    hidden = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert hidden.status_code == 200
    response = _complete(client, _employee(auth_header_factory))
    assert response.status_code == 400


def test_client_provided_price_and_totals_are_ignored(client, auth_header_factory):
    response = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={
            'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 2, 'unit_price': 1}],
            'payment_method': 'UPI',
            'unit_price': 1,
            'subtotal': 1,
            'discount_percent': 90,
            'discount_amount': 99,
            'gst_rate': 99,
            'gst_amount': 1,
            'cgst_amount': 1,
            'sgst_amount': 1,
            'total_amount': 1,
            'franchise_id': str(FRANCHISE_B),
            'status': 'DRAFT',
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body['franchise_id'] == str(FRANCHISE_A)
    assert body['subtotal'] == 44
    assert body['discount_amount'] == 0
    assert body['gst_rate'] == 5
    assert body['cgst_rate'] == 2.5
    assert body['sgst_rate'] == 2.5
    assert body['cgst_amount'] == 1.1
    assert body['sgst_amount'] == 1.1
    assert body['gst_amount'] == 2.2
    assert body['total_amount'] == 46.2
    assert body['status'] == 'COMPLETED'
    assert body['items'][0]['unit_price'] == 22


def test_current_franchise_selling_price_is_used(client, auth_header_factory):
    updated = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 30},
    )
    assert updated.status_code == 200
    response = _complete(client, _employee(auth_header_factory), items=[
        {'product_id': str(PRODUCT_NIMBU), 'quantity': 1},
    ])
    assert response.status_code == 201
    assert response.json()['items'][0]['unit_price'] == 30
    assert response.json()['subtotal'] == 30


# ── Quantity / cart ─────────────────────────────────────────────────────────


def test_quantity_must_be_at_least_one(client, auth_header_factory):
    response = _complete(client, _employee(auth_header_factory), items=[
        {'product_id': str(PRODUCT_NIMBU), 'quantity': 0},
    ])
    assert response.status_code == 422


def test_negative_quantity_rejected(client, auth_header_factory):
    response = _complete(client, _employee(auth_header_factory), items=[
        {'product_id': str(PRODUCT_NIMBU), 'quantity': -1},
    ])
    assert response.status_code == 422


def test_quantity_above_max_rejected(client, auth_header_factory):
    response = _complete(client, _employee(auth_header_factory), items=[
        {'product_id': str(PRODUCT_NIMBU), 'quantity': 1000},
    ])
    assert response.status_code == 422


def test_empty_cart_rejected(client, auth_header_factory):
    response = _complete(client, _employee(auth_header_factory), items=[])
    assert response.status_code == 422


def test_multiple_products_and_line_totals(client, auth_header_factory):
    _assign_orange(client, auth_header_factory, selling_price=40)
    response = _complete(
        client,
        _employee(auth_header_factory),
        items=[
            {'product_id': str(PRODUCT_NIMBU), 'quantity': 2},
            {'product_id': str(PRODUCT_ORANGE), 'quantity': 1},
        ],
    )
    assert response.status_code == 201
    body = response.json()
    by_name = {item['product_name_snapshot']: item for item in body['items']}
    assert by_name['Nimbu Pudina']['line_total'] == 44
    assert by_name['Nagpur Orange']['line_total'] == 40
    assert body['subtotal'] == 84
    assert body['taxable_amount'] == 84
    assert body['cgst_amount'] == 2.1
    assert body['sgst_amount'] == 2.1
    assert body['gst_amount'] == 4.2
    assert body['total_amount'] == 88.2


# ── GST ─────────────────────────────────────────────────────────────────────


def test_active_gst_rate_is_five_percent(client, auth_header_factory):
    menu = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory))
    assert menu.json()['gst_rate'] == 5
    assert menu.json()['cgst_rate'] == 2.5
    assert menu.json()['sgst_rate'] == 2.5
    body = _complete(client, _employee(auth_header_factory)).json()
    assert body['gst_rate'] == 5
    assert body['cgst_rate'] == 2.5
    assert body['sgst_rate'] == 2.5
    assert body['subtotal'] == 44
    assert body['discount_amount'] == 0
    assert body['taxable_amount'] == 44
    assert body['cgst_amount'] == 1.1
    assert body['sgst_amount'] == 1.1
    assert body['gst_amount'] == 2.2
    assert body['total_amount'] == 46.2


def test_gst_is_snapshotted_and_historical_order_unchanged(client, auth_header_factory, fake_db):
    created = _complete(client, _employee(auth_header_factory))
    assert created.status_code == 201
    order_id = created.json()['id']
    fake_db.tables['gst_settings'][0]['rate'] = 12
    fetched = client.get(f'/api/v1/pos/orders/{order_id}', headers=_employee(auth_header_factory))
    assert fetched.status_code == 200
    body = fetched.json()
    assert body['gst_rate'] == 5
    assert body['cgst_rate'] == 2.5
    assert body['sgst_rate'] == 2.5
    assert body['gst_amount'] == 2.2
    assert body['cgst_amount'] == 1.1
    assert body['sgst_amount'] == 1.1
    assert body['total_amount'] == 46.2

    later = _complete(client, _employee(auth_header_factory))
    assert later.status_code == 201
    assert later.json()['gst_rate'] == 12
    assert later.json()['cgst_rate'] == 6
    assert later.json()['sgst_rate'] == 6


def test_missing_gst_configuration_blocks_checkout(client, auth_header_factory, fake_db):
    fake_db.tables['gst_settings'].clear()
    before = len(fake_db.tables['orders'])
    response = _complete(client, _employee(auth_header_factory))
    assert response.status_code == 503
    assert 'GST' in response.json()['detail']
    assert len(fake_db.tables['orders']) == before


# ── Discount / invented payload ──────────────────────────────────────────────


def test_owner_cannot_apply_percentage_discount(client, auth_header_factory):
    response = _complete(client, _owner(auth_header_factory), offer_id=str(uuid4()))
    assert response.status_code == 403


def test_employee_invented_discount_percent_is_ignored(client, auth_header_factory):
    response = _complete(client, _employee(auth_header_factory), discount_percent=10)
    assert response.status_code == 201
    body = response.json()
    assert body['discount_amount'] == 0
    assert body['offer_id'] is None
    assert body['taxable_amount'] == body['subtotal']


def test_employee_zero_discount_allowed(client, auth_header_factory):
    response = _complete(client, _employee(auth_header_factory))
    assert response.status_code == 201
    assert response.json()['discount_amount'] == 0


def test_unknown_offer_is_rejected(client, auth_header_factory, fake_db):
    before = len(fake_db.tables['orders'])
    response = _complete(client, _employee(auth_header_factory), offer_id=str(uuid4()))
    assert response.status_code == 422
    assert len(fake_db.tables['orders']) == before


# ── Order lifecycle / snapshots / bill numbers ──────────────────────────────


def test_completed_order_has_payment_and_timestamp_and_items(client, auth_header_factory):
    body = _complete(client, _employee(auth_header_factory), payment_method='CASH').json()
    assert body['status'] == 'COMPLETED'
    assert body['payment_method'] == 'CASH'
    assert body['payment_status'] == 'PAID'
    assert body['completed_at']
    assert body['bill_number'] == 'RS-0001'
    assert len(body['items']) == 1
    assert body['cashier_id'] == str(EMPLOYEE_ID)
    assert body['cashier_name'] == 'Employee User'


def test_bill_numbers_are_sequential_and_unique_per_franchise(client, auth_header_factory):
    first = _complete(client, _employee(auth_header_factory))
    second = _complete(client, _employee(auth_header_factory), payment_method='CARD')
    assert first.json()['bill_number'] == 'RS-0001'
    assert second.json()['bill_number'] == 'RS-0002'
    assert first.json()['id'] != second.json()['id']


def test_concurrent_checkout_does_not_duplicate_bill_numbers(fake_db):
    from app.modules.pos.engine import complete_pos_order_atomic

    params = {
        'p_franchise_id': str(FRANCHISE_A),
        'p_cashier_id': str(EMPLOYEE_ID),
        'p_cashier_role': 'EMPLOYEE',
        'p_payment_method': 'UPI',
        'p_customer_phone': None,
        'p_offer_id': None,
        'p_items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 1}],
    }

    def _run(_):
        with fake_db.lock:
            return complete_pos_order_atomic(fake_db.tables, params)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(_run, range(4)))

    bills = [row['bill_number'] for row in results]
    assert len(set(bills)) == 4
    assert sorted(bills) == ['RS-0001', 'RS-0002', 'RS-0003', 'RS-0004']
    assert len(fake_db.tables['orders']) == 4
    assert all(row['status'] == 'COMPLETED' for row in fake_db.tables['orders'])


def test_failed_checkout_leaves_no_partial_order(client, auth_header_factory, fake_db):
    before_orders = len(fake_db.tables['orders'])
    before_items = len(fake_db.tables['order_items'])
    response = _complete(
        client,
        _employee(auth_header_factory),
        items=[
            {'product_id': str(PRODUCT_NIMBU), 'quantity': 1},
            {'product_id': str(PRODUCT_ORANGE), 'quantity': 1},
        ],
    )
    assert response.status_code == 400
    assert len(fake_db.tables['orders']) == before_orders
    assert len(fake_db.tables['order_items']) == before_items


# ── Payment ─────────────────────────────────────────────────────────────────


def test_cash_upi_and_card_payments(client, auth_header_factory):
    for method in ('CASH', 'UPI', 'CARD'):
        response = _complete(client, _employee(auth_header_factory), payment_method=method)
        assert response.status_code == 201
        assert response.json()['payment_method'] == method
        assert response.json()['status'] == 'COMPLETED'
        assert response.json()['completed_at']


def test_qr_payment_rejected(client, auth_header_factory):
    response = _complete(client, _employee(auth_header_factory), payment_method='QR')
    assert response.status_code == 422


def test_missing_payment_method_rejected(client, auth_header_factory):
    response = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 1}]},
    )
    assert response.status_code == 422


# ── Receipt / reprint ───────────────────────────────────────────────────────


def test_receipt_payload_contains_snapshots_and_totals(client, auth_header_factory):
    created = _complete(client, _employee(auth_header_factory), payment_method='CARD')
    order_id = created.json()['id']
    fetched = client.get(f'/api/v1/pos/orders/{order_id}', headers=_employee(auth_header_factory))
    assert fetched.status_code == 200
    body = fetched.json()
    assert body['bill_number'] == 'RS-0001'
    assert body['items'][0]['product_name_snapshot'] == 'Nimbu Pudina'
    assert body['items'][0]['unit_price'] == 22
    assert body['gst_rate'] == 5
    assert body['cgst_rate'] == 2.5
    assert body['sgst_rate'] == 2.5
    assert body['total_amount'] == 46.2
    assert body['payment_method'] == 'CARD'
    assert body['payment_status'] == 'PAID'
    assert body['franchise_name'] == 'Hyderabad — Main Store'


def test_reprint_does_not_create_another_order_or_bill_number(client, auth_header_factory, fake_db):
    created = _complete(client, _employee(auth_header_factory))
    order_id = created.json()['id']
    bill = created.json()['bill_number']
    first = client.get(f'/api/v1/pos/orders/{order_id}', headers=_employee(auth_header_factory))
    second = client.get(f'/api/v1/pos/orders/{order_id}', headers=_employee(auth_header_factory))
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()['bill_number'] == bill
    assert second.json()['bill_number'] == bill
    assert first.json()['total_amount'] == second.json()['total_amount']
    assert len(fake_db.tables['orders']) == 1


def test_unknown_order_is_not_found(client, auth_header_factory):
    response = client.get(f'/api/v1/pos/orders/{uuid4()}', headers=_employee(auth_header_factory))
    assert response.status_code == 404


def test_menu_hides_inactive_category_products(client, auth_header_factory, fake_db):
    zest = next(row for row in fake_db.tables['product_categories'] if row['name'] == 'Zest Collection')
    zest['is_active'] = False
    menu = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory)).json()
    assert all(item['product_id'] != str(PRODUCT_NIMBU) for item in menu['items'])
    assert all(cat['name'] != 'Zest Collection' for cat in menu['categories'])
