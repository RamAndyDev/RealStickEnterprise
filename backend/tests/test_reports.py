"""M9 reports and dashboards — authorization, aggregation, isolation, snapshots."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
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

REPORT_ENDPOINTS = (
    '/api/v1/reports/summary',
    '/api/v1/reports/daily',
    '/api/v1/reports/products',
    '/api/v1/reports/payments',
    '/api/v1/reports/dashboard/admin',
    '/api/v1/reports/dashboard/owner',
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


def _assign_orange_a(client, auth_header_factory, *, selling_price=40):
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


def _seed_order(
    fake_db,
    *,
    status: str,
    franchise_id,
    total_amount: float,
    payment_method: str | None = None,
    completed_at: str | None = None,
    items: list[dict] | None = None,
    bill_number: str | None = None,
):
    now = datetime.now(timezone.utc).isoformat()
    order_id = str(uuid4())
    fake_db.tables['orders'].append(
        {
            'id': order_id,
            'franchise_id': str(franchise_id),
            'bill_number': bill_number or f'RS-{uuid4().hex[:4].upper()}',
            'status': status,
            'total_amount': total_amount,
            'subtotal': total_amount,
            'payment_method': payment_method,
            'completed_at': completed_at,
            'cancelled_at': now if status == 'CANCELLED' else None,
            'created_at': now,
            'updated_at': now,
        }
    )
    for item in items or []:
        fake_db.tables['order_items'].append(
            {
                'id': str(uuid4()),
                'order_id': order_id,
                'product_id': item.get('product_id', str(PRODUCT_NIMBU)),
                'product_name_snapshot': item.get('product_name_snapshot', 'Nimbu Pudina'),
                'unit_price': item.get('unit_price', 22),
                'quantity': item.get('quantity', 1),
                'line_discount_amount': 0,
                'line_total': item.get('line_total', item.get('unit_price', 22) * item.get('quantity', 1)),
                'created_at': now,
            }
        )
    return order_id


def _activate_franchise_b(fake_db) -> None:
    for row in fake_db.tables['franchises']:
        if row['id'] == str(FRANCHISE_B):
            row['status'] = 'ACTIVE'


# ── Authorization ───────────────────────────────────────────────────────────


def test_unauthenticated_reports_are_rejected(client):
    for path in REPORT_ENDPOINTS:
        assert client.get(path).status_code == 401


def test_employee_is_forbidden_from_all_report_endpoints(client, auth_header_factory):
    headers = _employee(auth_header_factory)
    for path in REPORT_ENDPOINTS:
        response = client.get(path, headers=headers)
        assert response.status_code == 403, path
        assert response.json()['detail'] == 'Insufficient permissions for this resource'


def test_owner_cannot_access_admin_dashboard(client, auth_header_factory):
    response = client.get('/api/v1/reports/dashboard/admin', headers=_owner(auth_header_factory))
    assert response.status_code == 403


def test_admin_cannot_access_owner_dashboard(client, auth_header_factory):
    response = client.get('/api/v1/reports/dashboard/owner', headers=_admin(auth_header_factory))
    assert response.status_code == 403


# ── Empty data ──────────────────────────────────────────────────────────────


def test_empty_reports_return_zero_values(client, auth_header_factory):
    headers = _owner(auth_header_factory)
    summary = client.get('/api/v1/reports/summary', headers=headers, params={'period': 'today'})
    assert summary.status_code == 200
    body = summary.json()
    assert body['revenue'] == 0
    assert body['orders'] == 0
    assert body['avg_order'] == 0
    assert body['items_sold'] == 0
    assert body['recent_bills'] == []

    products = client.get('/api/v1/reports/products', headers=headers, params={'period': 'today'})
    assert products.status_code == 200
    assert products.json()['items'] == []

    payments = client.get('/api/v1/reports/payments', headers=headers, params={'period': 'today'})
    assert payments.status_code == 200
    methods = {row['payment_method']: row['amount'] for row in payments.json()['items']}
    assert methods == {'CASH': 0, 'UPI': 0, 'CARD': 0}

    daily = client.get('/api/v1/reports/daily', headers=headers, params={'period': 'today'})
    assert daily.status_code == 200
    assert daily.json()['items'] == [
        {'date': datetime.now(timezone.utc).date().isoformat(), 'revenue': 0}
    ]


def test_empty_admin_dashboard_counts_active_outlets(client, auth_header_factory):
    response = client.get('/api/v1/reports/dashboard/admin', headers=_admin(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['today_revenue'] == 0
    assert body['orders_today'] == 0
    assert body['active_outlets'] == 1
    assert body['top_seller_name'] is None
    assert body['top_seller_quantity'] == 0
    assert body['all_time_revenue'] == 0
    assert body['total_bills'] == 0
    names = {row['franchise_name'] for row in body['outlets']}
    assert 'Hyderabad — Main Store' in names
    assert 'Secunderabad Kiosk' in names
    assert all(row['revenue'] == 0 and row['orders'] == 0 for row in body['outlets'])


def test_empty_owner_dashboard_is_zero(client, auth_header_factory):
    response = client.get('/api/v1/reports/dashboard/owner', headers=_owner(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['franchise_id'] == str(FRANCHISE_A)
    assert body['franchise_name'] == 'Hyderabad — Main Store'
    assert body['today_revenue'] == 0
    assert body['bills_today'] == 0
    assert body['top_product_name'] is None
    assert body['all_time_revenue'] == 0
    assert body['recent_bills'] == []


# ── Aggregation ─────────────────────────────────────────────────────────────


def test_summary_aggregates_completed_orders(client, auth_header_factory):
    first = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    second = _checkout(
        client,
        _employee(auth_header_factory),
        items=[{'product_id': str(PRODUCT_NIMBU), 'quantity': 3}],
        payment_method='CARD',
    )
    assert first.status_code == 201
    assert second.status_code == 201

    expected_revenue = first.json()['total_amount'] + second.json()['total_amount']
    response = client.get(
        '/api/v1/reports/summary',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['revenue'] == expected_revenue
    assert body['orders'] == 2
    assert body['avg_order'] == round(expected_revenue / 2)
    assert body['items_sold'] == 5
    assert len(body['recent_bills']) == 2


def test_average_order_is_zero_when_no_orders(client, auth_header_factory):
    body = client.get(
        '/api/v1/reports/summary',
        headers=_admin(auth_header_factory),
        params={'period': '7d'},
    ).json()
    assert body['avg_order'] == 0


def test_revenue_uses_total_amount_not_subtotal(client, auth_header_factory, fake_db):
    created = _checkout(client, _employee(auth_header_factory))
    assert created.status_code == 201
    order = created.json()
    assert order['total_amount'] != order['subtotal']

    body = client.get(
        '/api/v1/reports/summary',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    ).json()
    assert body['revenue'] == order['total_amount']
    assert body['revenue'] != order['subtotal']


def test_top_products_use_snapshot_line_revenue(client, auth_header_factory):
    _assign_orange_a(client, auth_header_factory, selling_price=40)
    nimbu = _checkout(
        client,
        _employee(auth_header_factory),
        items=[{'product_id': str(PRODUCT_NIMBU), 'quantity': 5}],
        payment_method='CASH',
    )
    orange = _checkout(
        client,
        _employee(auth_header_factory),
        items=[{'product_id': str(PRODUCT_ORANGE), 'quantity': 2}],
        payment_method='UPI',
    )
    assert nimbu.status_code == 201
    assert orange.status_code == 201

    body = client.get(
        '/api/v1/reports/products',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    ).json()
    names = [row['product_name'] for row in body['items']]
    assert names[0] == 'Nimbu Pudina'
    assert body['items'][0]['quantity'] == 5
    assert body['items'][0]['revenue'] == 110
    assert names[1] == 'Nagpur Orange'
    assert body['items'][1]['quantity'] == 2
    assert body['items'][1]['revenue'] == 80


def test_top_products_limited_to_eight(client, auth_header_factory, fake_db):
    now = datetime.now(timezone.utc).isoformat()
    order_id = _seed_order(
        fake_db,
        status='COMPLETED',
        franchise_id=FRANCHISE_A,
        total_amount=900,
        payment_method='CASH',
        completed_at=now,
        items=[
            {
                'product_name_snapshot': f'Item {index}',
                'unit_price': 10 + index,
                'quantity': 1,
                'line_total': 10 + index,
            }
            for index in range(10)
        ],
    )
    assert order_id
    body = client.get(
        '/api/v1/reports/products',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    ).json()
    assert len(body['items']) == 8
    assert body['items'][0]['product_name'] == 'Item 9'


def test_payment_totals_group_cash_upi_card(client, auth_header_factory):
    assert _checkout(client, _employee(auth_header_factory), payment_method='CASH').status_code == 201
    assert _checkout(client, _employee(auth_header_factory), payment_method='UPI').status_code == 201
    assert _checkout(client, _employee(auth_header_factory), payment_method='CARD').status_code == 201

    body = client.get(
        '/api/v1/reports/payments',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    ).json()
    methods = {row['payment_method']: row['amount'] for row in body['items']}
    assert set(methods) == {'CASH', 'UPI', 'CARD'}
    assert methods['CASH'] > 0
    assert methods['UPI'] > 0
    assert methods['CARD'] > 0


def test_daily_revenue_fills_missing_days(client, auth_header_factory):
    created = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert created.status_code == 201
    today = datetime.now(timezone.utc).date().isoformat()

    today_series = client.get(
        '/api/v1/reports/daily',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    ).json()['items']
    assert len(today_series) == 1
    assert today_series[0]['date'] == today
    assert today_series[0]['revenue'] == created.json()['total_amount']

    week = client.get(
        '/api/v1/reports/daily',
        headers=_owner(auth_header_factory),
        params={'period': '7d'},
    ).json()['items']
    assert len(week) == 7
    assert week[-1]['date'] == today
    assert week[-1]['revenue'] == created.json()['total_amount']
    assert all(point['revenue'] == 0 for point in week[:-1])

    month = client.get(
        '/api/v1/reports/daily',
        headers=_owner(auth_header_factory),
        params={'period': '30d'},
    ).json()['items']
    assert len(month) == 7


# ── Filtering ───────────────────────────────────────────────────────────────


def test_draft_and_cancelled_orders_are_excluded(client, auth_header_factory, fake_db):
    completed = _checkout(client, _employee(auth_header_factory), payment_method='UPI')
    assert completed.status_code == 201
    now = datetime.now(timezone.utc).isoformat()
    _seed_order(
        fake_db,
        status='DRAFT',
        franchise_id=FRANCHISE_A,
        total_amount=9999,
        items=[{'quantity': 50, 'unit_price': 100, 'product_name_snapshot': 'Ghost Draft'}],
    )
    _seed_order(
        fake_db,
        status='CANCELLED',
        franchise_id=FRANCHISE_A,
        total_amount=8888,
        payment_method='CASH',
        completed_at=now,
        items=[{'quantity': 40, 'unit_price': 100, 'product_name_snapshot': 'Ghost Cancelled'}],
    )

    summary = client.get(
        '/api/v1/reports/summary',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    ).json()
    assert summary['orders'] == 1
    assert summary['revenue'] == completed.json()['total_amount']
    assert summary['items_sold'] == 2

    products = client.get(
        '/api/v1/reports/products',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    ).json()['items']
    names = {row['product_name'] for row in products}
    assert names == {'Nimbu Pudina'}


def test_period_filters_use_completed_at(client, auth_header_factory, fake_db):
    created = _checkout(client, _employee(auth_header_factory))
    assert created.status_code == 201
    order_id = created.json()['id']
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    row = next(item for item in fake_db.tables['orders'] if item['id'] == order_id)
    row['completed_at'] = old
    row['created_at'] = old

    today = client.get(
        '/api/v1/reports/summary',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    ).json()
    week = client.get(
        '/api/v1/reports/summary',
        headers=_owner(auth_header_factory),
        params={'period': '7d'},
    ).json()
    month = client.get(
        '/api/v1/reports/summary',
        headers=_owner(auth_header_factory),
        params={'period': '30d'},
    ).json()
    assert today['orders'] == 0
    assert week['orders'] == 0
    assert month['orders'] == 1
    assert month['revenue'] == created.json()['total_amount']


# ── Franchise isolation ─────────────────────────────────────────────────────


def test_owner_sees_only_own_franchise(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='UPI')
    assert other.status_code == 201

    owner = client.get(
        '/api/v1/reports/summary',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    ).json()
    assert owner['orders'] == 1
    assert owner['revenue'] == own.json()['total_amount']

    admin = client.get(
        '/api/v1/reports/summary',
        headers=_admin(auth_header_factory),
        params={'period': 'today'},
    ).json()
    assert admin['orders'] == 2
    assert admin['revenue'] == own.json()['total_amount'] + other.json()['total_amount']


def test_owner_supplied_franchise_id_cannot_widen_scope(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory))
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='CARD')
    assert other.status_code == 201

    for path in ('/api/v1/reports/summary', '/api/v1/reports/daily', '/api/v1/reports/products', '/api/v1/reports/payments'):
        response = client.get(
            path,
            headers=_owner(auth_header_factory),
            params={'period': 'today', 'franchise_id': str(FRANCHISE_B)},
        )
        assert response.status_code == 200, path
        if path.endswith('/summary'):
            assert response.json()['orders'] == 1
            assert response.json()['revenue'] == own.json()['total_amount']
        if path.endswith('/payments'):
            methods = {row['payment_method']: row['amount'] for row in response.json()['items']}
            assert methods['CARD'] == 0
            assert methods['UPI'] == own.json()['total_amount']


def test_admin_reports_are_all_franchises_even_if_franchise_id_sent(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory))
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory))
    assert other.status_code == 201

    body = client.get(
        '/api/v1/reports/summary',
        headers=_admin(auth_header_factory),
        params={'period': 'today', 'franchise_id': str(FRANCHISE_A)},
    ).json()
    assert body['orders'] == 2


# ── Dashboards ──────────────────────────────────────────────────────────────


def test_admin_dashboard_aggregates_today_and_all_time(client, auth_header_factory, fake_db):
    _activate_franchise_b(fake_db)
    _assign_orange_a(client, auth_header_factory, selling_price=40)
    today_nimbu = _checkout(
        client,
        _employee(auth_header_factory),
        items=[{'product_id': str(PRODUCT_NIMBU), 'quantity': 4}],
        payment_method='CASH',
    )
    today_orange = _checkout(
        client,
        _employee(auth_header_factory),
        items=[{'product_id': str(PRODUCT_ORANGE), 'quantity': 1}],
        payment_method='UPI',
    )
    assert today_nimbu.status_code == 201
    assert today_orange.status_code == 201

    _assign_nimbu_b(client, auth_header_factory)
    other_today = _checkout(client, _employee_b(auth_header_factory), payment_method='CARD')
    assert other_today.status_code == 201

    old_id = _checkout(client, _employee(auth_header_factory), payment_method='CASH').json()['id']
    old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    row = next(item for item in fake_db.tables['orders'] if item['id'] == old_id)
    row['completed_at'] = old
    row['created_at'] = old
    old_total = next(item for item in fake_db.tables['orders'] if item['id'] == old_id)['total_amount']

    body = client.get('/api/v1/reports/dashboard/admin', headers=_admin(auth_header_factory)).json()
    today_revenue = (
        Decimal(str(today_nimbu.json()['total_amount']))
        + Decimal(str(today_orange.json()['total_amount']))
        + Decimal(str(other_today.json()['total_amount']))
    )
    assert Decimal(str(body['today_revenue'])) == today_revenue
    assert body['orders_today'] == 3
    assert body['active_outlets'] == 2
    assert body['top_seller_name'] == 'Nimbu Pudina'
    assert body['top_seller_quantity'] == 6
    assert body['total_bills'] == 4
    assert Decimal(str(body['all_time_revenue'])) == today_revenue + Decimal(str(old_total))

    by_name = {row['franchise_name']: row for row in body['outlets']}
    assert by_name['Hyderabad — Main Store']['orders'] == 2
    assert by_name['Secunderabad Kiosk']['orders'] == 1
    assert Decimal(str(by_name['Hyderabad — Main Store']['revenue'])) == (
        Decimal(str(today_nimbu.json()['total_amount']))
        + Decimal(str(today_orange.json()['total_amount']))
    )


def test_active_outlets_come_from_franchise_status_not_orders(client, auth_header_factory, fake_db):
    _activate_franchise_b(fake_db)
    body = client.get('/api/v1/reports/dashboard/admin', headers=_admin(auth_header_factory)).json()
    assert body['active_outlets'] == 2
    assert body['orders_today'] == 0


def test_owner_dashboard_is_scoped_and_links_recent_bills(client, auth_header_factory):
    created = _checkout(client, _employee(auth_header_factory), payment_method='CARD')
    assert created.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='CASH')
    assert other.status_code == 201

    body = client.get('/api/v1/reports/dashboard/owner', headers=_owner(auth_header_factory)).json()
    assert body['franchise_id'] == str(FRANCHISE_A)
    assert body['today_revenue'] == created.json()['total_amount']
    assert body['bills_today'] == 1
    assert body['top_product_name'] == 'Nimbu Pudina'
    assert body['top_product_quantity'] == 2
    assert body['all_time_revenue'] == created.json()['total_amount']
    assert len(body['recent_bills']) == 1
    bill = body['recent_bills'][0]
    assert bill['id'] == created.json()['id']
    assert bill['bill_number'] == created.json()['bill_number']
    assert bill['total_amount'] == created.json()['total_amount']


def test_owner_dashboard_recent_bills_limited_to_today(client, auth_header_factory, fake_db):
    today = _checkout(client, _employee(auth_header_factory))
    assert today.status_code == 201
    old_id = _checkout(client, _employee(auth_header_factory)).json()['id']
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    row = next(item for item in fake_db.tables['orders'] if item['id'] == old_id)
    row['completed_at'] = old

    body = client.get('/api/v1/reports/dashboard/owner', headers=_owner(auth_header_factory)).json()
    assert body['bills_today'] == 1
    assert [bill['id'] for bill in body['recent_bills']] == [today.json()['id']]
    assert body['all_time_revenue'] == today.json()['total_amount'] + next(
        item for item in fake_db.tables['orders'] if item['id'] == old_id
    )['total_amount']


# ── Snapshot integrity ──────────────────────────────────────────────────────


def test_reports_use_historical_snapshots_not_live_prices(client, auth_header_factory):
    offer = _create_offer(client, auth_header_factory)
    created = _checkout(
        client,
        _employee(auth_header_factory),
        items=[{'product_id': str(PRODUCT_NIMBU), 'quantity': 2}],
        payment_method='UPI',
        offer_id=offer['id'],
    )
    assert created.status_code == 201
    original_total = created.json()['total_amount']
    original_line = created.json()['items'][0]['unit_price'] * created.json()['items'][0]['quantity']

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

    summary = client.get(
        '/api/v1/reports/summary',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    ).json()
    products = client.get(
        '/api/v1/reports/products',
        headers=_owner(auth_header_factory),
        params={'period': 'today'},
    ).json()['items']
    dashboard = client.get('/api/v1/reports/dashboard/owner', headers=_owner(auth_header_factory)).json()

    assert summary['revenue'] == original_total
    assert summary['orders'] == 1
    assert products[0]['product_name'] == 'Nimbu Pudina'
    assert products[0]['revenue'] == original_line
    assert dashboard['today_revenue'] == original_total
    assert dashboard['top_product_name'] == 'Nimbu Pudina'
