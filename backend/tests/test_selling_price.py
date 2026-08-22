"""Selling-price rule: selling_price > 0, independent of master price."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.modules.products.pricing import (
    SELLING_PRICE_NOT_POSITIVE,
    validate_selling_price,
)
from tests.conftest import (
    ADMIN_ID,
    CATEGORY_GARDEN,
    FRANCHISE_A,
    FRANCHISE_B,
    OWNER_ID,
)

MIGRATIONS = Path(__file__).resolve().parents[2] / 'supabase' / 'migrations'
MIGRATION_0007 = MIGRATIONS / '0007_business_rules.sql'
MIGRATION_0011 = MIGRATIONS / '0011_allow_selling_price_equal_master.sql'
MIGRATION_0012 = MIGRATIONS / '0012_decouple_master_and_franchise_selling_prices.sql'


def _admin(auth_header_factory):
    return auth_header_factory(ADMIN_ID, 'admin@realstick.in')


def _owner(auth_header_factory):
    return auth_header_factory(OWNER_ID, 'owner@realstick.in')


def _create_priced_product(client, auth_header_factory, *, name: str, master: float = 100):
    created = client.post(
        '/api/v1/admin/products',
        headers=_admin(auth_header_factory),
        json={
            'name': name,
            'category_id': str(CATEGORY_GARDEN),
            'price': master,
            'is_active': True,
        },
    )
    assert created.status_code == 201, created.text
    return created.json()


def _assert_immutable_function_replace_only(sql: str) -> None:
    lowered = sql.lower()
    assert 'drop trigger' not in lowered
    assert 'create trigger' not in lowered
    assert 'drop table' not in lowered
    assert 'alter table' not in lowered
    assert 'create table' not in lowered
    assert 'enable row level security' not in lowered
    assert 'update public.products' not in lowered
    assert 'update public.franchise_product_prices' not in lowered
    assert 'delete from public.products' not in lowered
    assert 'delete from public.franchise_product_prices' not in lowered


def test_migration_0007_is_unchanged_and_still_has_old_comparisons():
    assert MIGRATION_0007.exists()
    sql = MIGRATION_0007.read_text(encoding='utf-8')
    lowered = sql.lower()
    assert 'new.selling_price >= v_master' in lowered
    assert 'fpp.selling_price >= new.price' in lowered
    assert 'Selling price must be strictly less than the master price' in sql


def test_migration_0011_is_unchanged_and_still_has_equal_master_rule():
    assert MIGRATION_0011.exists()
    sql = MIGRATION_0011.read_text(encoding='utf-8')
    lowered = sql.lower()

    assert 'create or replace function public.enforce_franchise_selling_price()' in lowered
    assert 'create or replace function public.enforce_master_price_above_selling()' in lowered
    assert 'returns trigger' in lowered
    assert 'v_master numeric(12, 2)' in lowered
    assert 'new.selling_price is null or new.selling_price <= 0' in lowered
    assert "raise exception 'product not found'" in lowered

    assert 'new.selling_price > v_master' in lowered
    assert 'new.selling_price >= v_master' not in lowered
    assert 'fpp.selling_price > new.price' in lowered
    assert 'fpp.selling_price >= new.price' not in lowered
    assert 'Selling price must not exceed the master price' in sql
    assert 'strictly less than the master price' not in sql
    assert 'Master price cannot be reduced below existing franchise selling prices.' in sql

    _assert_immutable_function_replace_only(sql)


def test_migration_0012_replaces_functions_and_removes_cross_price_enforcement():
    assert MIGRATION_0012.exists()
    sql = MIGRATION_0012.read_text(encoding='utf-8')
    lowered = sql.lower()

    assert 'create or replace function public.enforce_franchise_selling_price()' in lowered
    assert 'create or replace function public.enforce_master_price_above_selling()' in lowered
    assert 'returns trigger' in lowered
    assert 'new.selling_price is null or new.selling_price <= 0' in lowered
    assert "raise exception 'selling price must be greater than 0'" in lowered
    assert 'return new' in lowered

    assert 'v_master' not in lowered
    assert 'from public.products' not in lowered
    assert 'from public.franchise_product_prices' not in lowered
    assert 'new.selling_price > v_master' not in lowered
    assert 'new.selling_price >= v_master' not in lowered
    assert 'new.selling_price < v_master' not in lowered
    assert 'new.selling_price <= v_master' not in lowered
    assert 'fpp.selling_price > new.price' not in lowered
    assert 'fpp.selling_price >= new.price' not in lowered
    assert 'fpp.selling_price < new.price' not in lowered
    assert 'fpp.selling_price <= new.price' not in lowered
    assert 'must not exceed the master price' not in lowered
    assert 'strictly less than the master price' not in lowered
    assert 'cannot be reduced below existing franchise selling prices' not in lowered
    assert 'product not found' not in lowered

    _assert_immutable_function_replace_only(sql)


def test_validate_selling_price_below_master_passes():
    validate_selling_price(80)
    validate_selling_price(99)
    validate_selling_price('0.01')


def test_validate_selling_price_equal_to_master_passes():
    validate_selling_price(100)
    validate_selling_price('100.00')


def test_validate_selling_price_above_master_passes():
    validate_selling_price(101)
    validate_selling_price(120)
    validate_selling_price('150.00')


def test_validate_selling_price_much_higher_than_master_passes():
    validate_selling_price(500)
    validate_selling_price('999.99')


def test_validate_selling_price_zero_fails():
    with pytest.raises(HTTPException) as exc:
        validate_selling_price(0)
    assert exc.value.status_code == 400
    assert exc.value.detail == SELLING_PRICE_NOT_POSITIVE


def test_validate_selling_price_negative_fails():
    with pytest.raises(HTTPException) as exc:
        validate_selling_price(-1)
    assert exc.value.status_code == 400
    assert exc.value.detail == SELLING_PRICE_NOT_POSITIVE


def test_validate_selling_price_null_fails():
    with pytest.raises(HTTPException) as exc:
        validate_selling_price(None)
    assert exc.value.status_code == 400
    assert exc.value.detail == SELLING_PRICE_NOT_POSITIVE


def test_admin_assign_selling_price_rule(client, auth_header_factory):
    product = _create_priced_product(
        client, auth_header_factory, name='Assign Price Rule Stick', master=100
    )

    below = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 80, 'is_active': True},
    )
    assert below.status_code == 201
    assert below.json()['selling_price'] == 80

    equal = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{product["id"]}',
        headers=_admin(auth_header_factory),
        json={'selling_price': 100},
    )
    assert equal.status_code == 200
    assert equal.json()['selling_price'] == 100

    above = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{product["id"]}',
        headers=_admin(auth_header_factory),
        json={'selling_price': 120},
    )
    assert above.status_code == 200
    assert above.json()['selling_price'] == 120

    much_higher = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{product["id"]}',
        headers=_admin(auth_header_factory),
        json={'selling_price': 150},
    )
    assert much_higher.status_code == 200
    assert much_higher.json()['selling_price'] == 150

    zero = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{product["id"]}',
        headers=_admin(auth_header_factory),
        json={'selling_price': 0},
    )
    assert zero.status_code in {400, 422}

    negative = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{product["id"]}',
        headers=_admin(auth_header_factory),
        json={'selling_price': -1},
    )
    assert negative.status_code in {400, 422}

    null = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{product["id"]}',
        headers=_admin(auth_header_factory),
        json={'selling_price': None},
    )
    assert null.status_code in {400, 422}

    still = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
    )
    item = next(i for i in still.json()['items'] if i['product_id'] == product['id'])
    assert item['selling_price'] == 150
    assert item['master_price'] == 100


def test_admin_create_assignment_allows_above_and_rejects_zero_negative_null(
    client, auth_header_factory
):
    product = _create_priced_product(
        client, auth_header_factory, name='Create Price Rule Stick', master=100
    )

    above = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 120, 'is_active': True},
    )
    assert above.status_code == 201
    assert above.json()['selling_price'] == 120

    zero = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 0, 'is_active': True},
    )
    assert zero.status_code in {400, 422}

    negative = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': -1, 'is_active': True},
    )
    assert negative.status_code in {400, 422}

    null = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': None, 'is_active': True},
    )
    assert null.status_code in {400, 422}

    equal = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 100, 'is_active': True},
    )
    assert equal.status_code == 201
    assert equal.json()['selling_price'] == 100


def test_owner_update_selling_price_rule(client, auth_header_factory):
    product = _create_priced_product(
        client, auth_header_factory, name='Owner Price Rule Stick', master=100
    )
    assigned = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 90, 'is_active': True},
    )
    assert assigned.status_code == 201

    below = client.patch(
        f'/api/v1/owner/menu/{product["id"]}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 80},
    )
    assert below.status_code == 200
    assert below.json()['selling_price'] == 80

    equal = client.patch(
        f'/api/v1/owner/menu/{product["id"]}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 100},
    )
    assert equal.status_code == 200
    assert equal.json()['selling_price'] == 100

    above = client.patch(
        f'/api/v1/owner/menu/{product["id"]}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 120},
    )
    assert above.status_code == 200
    assert above.json()['selling_price'] == 120

    much_higher = client.patch(
        f'/api/v1/owner/menu/{product["id"]}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 150},
    )
    assert much_higher.status_code == 200
    assert much_higher.json()['selling_price'] == 150

    zero = client.patch(
        f'/api/v1/owner/menu/{product["id"]}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 0},
    )
    assert zero.status_code in {400, 422}

    negative = client.patch(
        f'/api/v1/owner/menu/{product["id"]}',
        headers=_owner(auth_header_factory),
        json={'selling_price': -1},
    )
    assert negative.status_code in {400, 422}

    null = client.patch(
        f'/api/v1/owner/menu/{product["id"]}',
        headers=_owner(auth_header_factory),
        json={'selling_price': None},
    )
    assert null.status_code in {400, 422}


def test_master_price_can_move_independently_of_franchise_selling_prices(
    client, auth_header_factory, fake_db
):
    product = _create_priced_product(
        client, auth_header_factory, name='Independent Master Stick', master=100
    )
    assigned = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 150, 'is_active': True},
    )
    assert assigned.status_code == 201

    reduced = client.patch(
        f'/api/v1/admin/products/{product["id"]}',
        headers=_admin(auth_header_factory),
        json={'price': 90},
    )
    assert reduced.status_code == 200
    assert reduced.json()['price'] == 90

    assignment = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == product['id']
    )
    assert float(assignment['selling_price']) == 150

    increased = client.patch(
        f'/api/v1/admin/products/{product["id"]}',
        headers=_admin(auth_header_factory),
        json={'price': 200},
    )
    assert increased.status_code == 200
    assert increased.json()['price'] == 200

    still = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == product['id']
    )
    assert float(still['selling_price']) == 150

    listed = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
    )
    item = next(i for i in listed.json()['items'] if i['product_id'] == product['id'])
    assert item['selling_price'] == 150
    assert item['master_price'] == 200


def test_multiple_franchises_can_have_different_selling_prices(client, auth_header_factory):
    product = _create_priced_product(
        client, auth_header_factory, name='Multi Franchise Price Stick', master=100
    )

    franchise_a = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 80, 'is_active': True},
    )
    franchise_b = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 150, 'is_active': True},
    )
    assert franchise_a.status_code == 201
    assert franchise_b.status_code == 201
    assert franchise_a.json()['selling_price'] == 80
    assert franchise_b.json()['selling_price'] == 150
    assert franchise_a.json()['master_price'] == 100
    assert franchise_b.json()['master_price'] == 100

    listed_a = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
    )
    listed_b = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
    )
    item_a = next(i for i in listed_a.json()['items'] if i['product_id'] == product['id'])
    item_b = next(i for i in listed_b.json()['items'] if i['product_id'] == product['id'])
    assert item_a['selling_price'] == 80
    assert item_b['selling_price'] == 150
