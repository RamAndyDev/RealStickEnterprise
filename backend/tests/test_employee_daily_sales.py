"""M9.1 / M9.2 employee daily sales — authorization, isolation, selected-date aggregation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from tests.conftest import FRANCHISE_A, FRANCHISE_B, PRODUCT_NIMBU
from tests.test_reports import (
    _admin,
    _assign_nimbu_b,
    _checkout,
    _create_offer,
    _employee,
    _employee_b,
    _owner,
    _seed_order,
)

EMPLOYEE_DAILY = '/api/v1/reports/employee/daily'


def _daily(client, headers, **params):
    return client.get(EMPLOYEE_DAILY, headers=headers, params=params or None)


def _utc_today():
    return datetime.now(timezone.utc).date()


def _shift_completed(fake_db, order_id: str, when: str) -> None:
    row = next(item for item in fake_db.tables['orders'] if item['id'] == order_id)
    row['completed_at'] = when
    row['created_at'] = when


# ── Authorization ───────────────────────────────────────────────────────────


def test_employee_can_access_daily_sales(client, auth_header_factory):
    response = _daily(client, _employee(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['date'] == datetime.now(timezone.utc).date().isoformat()
    assert body['summary']['revenue'] == 0
    assert body['bills'] == []


def test_unauthenticated_daily_sales_is_rejected(client):
    assert client.get(EMPLOYEE_DAILY).status_code == 401


def test_admin_cannot_use_employee_daily_sales(client, auth_header_factory):
    response = _daily(client, _admin(auth_header_factory))
    assert response.status_code == 403
    assert response.json()['detail'] == 'Insufficient permissions for this resource'


def test_owner_cannot_use_employee_daily_sales(client, auth_header_factory):
    response = _daily(client, _owner(auth_header_factory))
    assert response.status_code == 403
    assert response.json()['detail'] == 'Insufficient permissions for this resource'


# ── Franchise isolation ─────────────────────────────────────────────────────


def test_employee_sees_only_own_franchise(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='UPI')
    assert other.status_code == 201

    own_body = _daily(client, _employee(auth_header_factory)).json()
    assert own_body['summary']['bills'] == 1
    assert own_body['summary']['revenue'] == own.json()['total_amount']
    assert [bill['id'] for bill in own_body['bills']] == [own.json()['id']]

    other_body = _daily(client, _employee_b(auth_header_factory)).json()
    assert other_body['summary']['bills'] == 1
    assert other_body['summary']['revenue'] == other.json()['total_amount']
    assert [bill['id'] for bill in other_body['bills']] == [other.json()['id']]


def test_client_supplied_franchise_id_cannot_widen_access(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='CARD')
    assert other.status_code == 201

    body = _daily(
        client,
        _employee(auth_header_factory),
        franchise_id=str(FRANCHISE_B),
    ).json()
    assert body['summary']['bills'] == 1
    assert body['summary']['revenue'] == own.json()['total_amount']
    assert body['payments']['card'] == 0
    assert [bill['id'] for bill in body['bills']] == [own.json()['id']]


# ── Date filtering ──────────────────────────────────────────────────────────


def test_today_completed_orders_are_included(client, auth_header_factory):
    created = _checkout(client, _employee(auth_header_factory), payment_method='UPI')
    assert created.status_code == 201
    body = _daily(client, _employee(auth_header_factory)).json()
    assert body['summary']['bills'] == 1
    assert body['bills'][0]['id'] == created.json()['id']
    assert body['bills'][0]['bill_number'] == created.json()['bill_number']


def test_previous_day_orders_are_excluded(client, auth_header_factory, fake_db):
    created = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert created.status_code == 201
    old = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    row = next(item for item in fake_db.tables['orders'] if item['id'] == created.json()['id'])
    row['completed_at'] = old
    row['created_at'] = old

    body = _daily(client, _employee(auth_header_factory)).json()
    assert body['summary']['bills'] == 0
    assert body['summary']['revenue'] == 0
    assert body['bills'] == []


def test_future_orders_are_excluded(client, auth_header_factory, fake_db):
    created = _checkout(client, _employee(auth_header_factory), payment_method='CARD')
    assert created.status_code == 201
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    row = next(item for item in fake_db.tables['orders'] if item['id'] == created.json()['id'])
    row['completed_at'] = future

    body = _daily(client, _employee(auth_header_factory)).json()
    assert body['summary']['bills'] == 0
    assert body['bills'] == []


# ── Status ──────────────────────────────────────────────────────────────────


def test_completed_orders_included_draft_and_cancelled_excluded(client, auth_header_factory, fake_db):
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

    body = _daily(client, _employee(auth_header_factory)).json()
    assert body['summary']['bills'] == 1
    assert body['summary']['revenue'] == completed.json()['total_amount']
    assert body['summary']['items_sold'] == 2
    assert body['payments']['cash'] == 0
    assert [bill['id'] for bill in body['bills']] == [completed.json()['id']]


# ── Calculations ────────────────────────────────────────────────────────────


def test_daily_sales_aggregates_revenue_bills_items_and_average(client, auth_header_factory):
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
    body = _daily(client, _employee(auth_header_factory)).json()
    assert body['summary']['revenue'] == expected_revenue
    assert body['summary']['bills'] == 2
    assert body['summary']['items_sold'] == 5
    assert body['summary']['average_bill'] == round(expected_revenue / 2)
    assert len(body['bills']) == 2


def test_revenue_uses_total_amount_not_subtotal(client, auth_header_factory):
    created = _checkout(client, _employee(auth_header_factory), payment_method='UPI')
    assert created.status_code == 201
    order = created.json()
    assert order['total_amount'] != order['subtotal']

    body = _daily(client, _employee(auth_header_factory)).json()
    assert body['summary']['revenue'] == order['total_amount']
    assert body['summary']['revenue'] != order['subtotal']


def test_payment_totals_group_cash_upi_card(client, auth_header_factory):
    cash = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    upi = _checkout(client, _employee(auth_header_factory), payment_method='UPI')
    card = _checkout(client, _employee(auth_header_factory), payment_method='CARD')
    assert cash.status_code == 201
    assert upi.status_code == 201
    assert card.status_code == 201

    body = _daily(client, _employee(auth_header_factory)).json()
    assert body['payments']['cash'] == cash.json()['total_amount']
    assert body['payments']['upi'] == upi.json()['total_amount']
    assert body['payments']['card'] == card.json()['total_amount']


# ── Empty data ──────────────────────────────────────────────────────────────


def test_no_sales_returns_zero_summary_and_empty_bills(client, auth_header_factory):
    body = _daily(client, _employee(auth_header_factory)).json()
    assert body['summary'] == {
        'revenue': 0,
        'bills': 0,
        'items_sold': 0,
        'average_bill': 0,
    }
    assert body['payments'] == {'cash': 0, 'upi': 0, 'card': 0}
    assert body['bills'] == []


# ── Historical snapshots ────────────────────────────────────────────────────


def test_daily_sales_use_historical_snapshots_not_live_prices(client, auth_header_factory):
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

    body = _daily(client, _employee(auth_header_factory)).json()
    assert body['summary']['revenue'] == original_total
    assert body['summary']['bills'] == 1
    assert body['payments']['upi'] == original_total
    assert Decimal(str(body['summary']['revenue'])) == Decimal(str(original_total))


# ── M9.2 selected date ──────────────────────────────────────────────────────


def test_employee_can_request_today_with_date_param(client, auth_header_factory):
    created = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert created.status_code == 201
    today = _utc_today().isoformat()
    body = _daily(client, _employee(auth_header_factory), date=today).json()
    assert body['date'] == today
    assert body['summary']['bills'] == 1
    assert body['summary']['revenue'] == created.json()['total_amount']
    assert [bill['id'] for bill in body['bills']] == [created.json()['id']]


def test_employee_can_request_a_previous_date(client, auth_header_factory, fake_db):
    created = _checkout(client, _employee(auth_header_factory), payment_method='UPI')
    assert created.status_code == 201
    previous = _utc_today() - timedelta(days=1)
    _shift_completed(
        fake_db,
        created.json()['id'],
        datetime.combine(previous, datetime.min.time().replace(hour=15), tzinfo=timezone.utc).isoformat(),
    )

    body = _daily(client, _employee(auth_header_factory), date=previous.isoformat()).json()
    assert body['date'] == previous.isoformat()
    assert body['summary']['bills'] == 1
    assert body['summary']['revenue'] == created.json()['total_amount']
    assert [bill['id'] for bill in body['bills']] == [created.json()['id']]


def test_previous_date_returns_only_that_dates_completed_orders(client, auth_header_factory, fake_db):
    today_order = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    previous_order = _checkout(client, _employee(auth_header_factory), payment_method='UPI')
    older_order = _checkout(client, _employee(auth_header_factory), payment_method='CARD')
    assert today_order.status_code == 201
    assert previous_order.status_code == 201
    assert older_order.status_code == 201

    previous = _utc_today() - timedelta(days=1)
    older = _utc_today() - timedelta(days=3)
    _shift_completed(
        fake_db,
        previous_order.json()['id'],
        datetime.combine(previous, datetime.min.time(), tzinfo=timezone.utc).isoformat(),
    )
    _shift_completed(
        fake_db,
        older_order.json()['id'],
        datetime.combine(older, datetime.min.time(), tzinfo=timezone.utc).isoformat(),
    )

    body = _daily(client, _employee(auth_header_factory), date=previous.isoformat()).json()
    assert body['date'] == previous.isoformat()
    assert body['summary']['bills'] == 1
    assert [bill['id'] for bill in body['bills']] == [previous_order.json()['id']]
    assert today_order.json()['id'] not in [bill['id'] for bill in body['bills']]
    assert older_order.json()['id'] not in [bill['id'] for bill in body['bills']]


def test_today_orders_are_excluded_when_another_date_is_selected(client, auth_header_factory, fake_db):
    today_order = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    previous_order = _checkout(client, _employee(auth_header_factory), payment_method='UPI')
    assert today_order.status_code == 201
    assert previous_order.status_code == 201
    previous = _utc_today() - timedelta(days=2)
    _shift_completed(
        fake_db,
        previous_order.json()['id'],
        datetime.combine(previous, datetime.min.time(), tzinfo=timezone.utc).isoformat(),
    )

    selected = _daily(client, _employee(auth_header_factory), date=previous.isoformat()).json()
    assert selected['summary']['bills'] == 1
    assert [bill['id'] for bill in selected['bills']] == [previous_order.json()['id']]

    today_body = _daily(client, _employee(auth_header_factory)).json()
    assert today_body['summary']['bills'] == 1
    assert [bill['id'] for bill in today_body['bills']] == [today_order.json()['id']]


def test_future_date_is_rejected(client, auth_header_factory):
    future = (_utc_today() + timedelta(days=1)).isoformat()
    response = _daily(client, _employee(auth_header_factory), date=future)
    assert response.status_code == 422
    assert 'future' in str(response.json()['detail']).lower()


def test_invalid_date_format_is_rejected(client, auth_header_factory):
    headers = _employee(auth_header_factory)
    assert _daily(client, headers, date='15-08-2026').status_code == 422
    assert _daily(client, headers, date='not-a-date').status_code == 422
    assert _daily(client, headers, date='2026/08/15').status_code == 422


def test_selected_date_excludes_draft_and_cancelled(client, auth_header_factory, fake_db):
    previous = _utc_today() - timedelta(days=4)
    when = datetime.combine(
        previous, datetime.min.time().replace(hour=10), tzinfo=timezone.utc
    ).isoformat()
    completed = _checkout(client, _employee(auth_header_factory), payment_method='UPI')
    assert completed.status_code == 201
    _shift_completed(fake_db, completed.json()['id'], when)
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
        completed_at=when,
        items=[{'quantity': 40, 'unit_price': 100, 'product_name_snapshot': 'Ghost Cancelled'}],
    )

    body = _daily(client, _employee(auth_header_factory), date=previous.isoformat()).json()
    assert body['summary']['bills'] == 1
    assert body['summary']['revenue'] == completed.json()['total_amount']
    assert body['summary']['items_sold'] == 2
    assert body['payments']['cash'] == 0
    assert [bill['id'] for bill in body['bills']] == [completed.json()['id']]


def test_selected_date_aggregates_revenue_bills_items_average_and_payments(
    client, auth_header_factory, fake_db
):
    previous = _utc_today() - timedelta(days=5)
    when = datetime.combine(
        previous, datetime.min.time().replace(hour=9), tzinfo=timezone.utc
    ).isoformat()
    cash = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    upi = _checkout(client, _employee(auth_header_factory), payment_method='UPI')
    card = _checkout(
        client,
        _employee(auth_header_factory),
        items=[{'product_id': str(PRODUCT_NIMBU), 'quantity': 3}],
        payment_method='CARD',
    )
    assert cash.status_code == 201
    assert upi.status_code == 201
    assert card.status_code == 201
    for created in (cash, upi, card):
        _shift_completed(fake_db, created.json()['id'], when)

    expected_revenue = cash.json()['total_amount'] + upi.json()['total_amount'] + card.json()['total_amount']
    body = _daily(client, _employee(auth_header_factory), date=previous.isoformat()).json()
    assert body['summary']['revenue'] == expected_revenue
    assert body['summary']['bills'] == 3
    assert body['summary']['items_sold'] == 7
    assert body['summary']['average_bill'] == round(expected_revenue / 3)
    assert body['payments']['cash'] == cash.json()['total_amount']
    assert body['payments']['upi'] == upi.json()['total_amount']
    assert body['payments']['card'] == card.json()['total_amount']


def test_empty_historical_date_returns_zero_values(client, auth_header_factory):
    created = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert created.status_code == 201
    empty_day = (_utc_today() - timedelta(days=12)).isoformat()
    body = _daily(client, _employee(auth_header_factory), date=empty_day).json()
    assert body['date'] == empty_day
    assert body['summary'] == {
        'revenue': 0,
        'bills': 0,
        'items_sold': 0,
        'average_bill': 0,
    }
    assert body['payments'] == {'cash': 0, 'upi': 0, 'card': 0}
    assert body['bills'] == []


def test_selected_date_stays_scoped_to_employee_franchise(client, auth_header_factory, fake_db):
    own = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='UPI')
    assert other.status_code == 201
    previous = _utc_today() - timedelta(days=6)
    when = datetime.combine(previous, datetime.min.time(), tzinfo=timezone.utc).isoformat()
    _shift_completed(fake_db, own.json()['id'], when)
    _shift_completed(fake_db, other.json()['id'], when)

    own_body = _daily(
        client,
        _employee(auth_header_factory),
        date=previous.isoformat(),
        franchise_id=str(FRANCHISE_B),
    ).json()
    assert own_body['summary']['bills'] == 1
    assert own_body['summary']['revenue'] == own.json()['total_amount']
    assert [bill['id'] for bill in own_body['bills']] == [own.json()['id']]


def test_historical_snapshots_unchanged_for_selected_past_date(client, auth_header_factory, fake_db):
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
    previous = _utc_today() - timedelta(days=8)
    _shift_completed(
        fake_db,
        created.json()['id'],
        datetime.combine(previous, datetime.min.time().replace(hour=11), tzinfo=timezone.utc).isoformat(),
    )

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

    body = _daily(client, _employee(auth_header_factory), date=previous.isoformat()).json()
    assert body['summary']['revenue'] == original_total
    assert body['summary']['bills'] == 1
    assert body['payments']['upi'] == original_total
    assert Decimal(str(body['summary']['revenue'])) == Decimal(str(original_total))
