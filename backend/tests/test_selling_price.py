"""Selling-price rule: 0 < selling_price <= master_price."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.modules.products.pricing import (
    SELLING_PRICE_EXCEEDS_MASTER,
    SELLING_PRICE_NOT_POSITIVE,
    selling_price_conflicts_with_master,
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


def test_migration_0011_replaces_selling_price_functions_only():
    assert MIGRATION_0011.exists()
    sql = MIGRATION_0011.read_text(encoding='utf-8')
    lowered = sql.lower()

    assert 'create or replace function public.enforce_franchise_selling_price()' in lowered
    assert 'create or replace function public.enforce_master_price_above_selling()' in lowered
    assert 'returns trigger' in lowered
    assert 'v_master numeric(12, 2)' in lowered
    assert 'new.selling_price is null or new.selling_price <= 0' in lowered
    assert 'raise exception \'product not found\'' in lowered

    assert 'new.selling_price > v_master' in lowered
    assert 'new.selling_price >= v_master' not in lowered
    assert 'fpp.selling_price > new.price' in lowered
    assert 'fpp.selling_price >= new.price' not in lowered
    assert 'Selling price must not exceed the master price' in sql
    assert 'strictly less than the master price' not in sql
    assert 'Master price cannot be reduced below existing franchise selling prices.' in sql

    assert 'drop trigger' not in lowered
    assert 'create trigger' not in lowered
    assert 'drop table' not in lowered
    assert 'alter table' not in lowered
    assert 'create table' not in lowered
    assert 'enable row level security' not in lowered
    assert 'update public.products' not in lowered
    assert 'update public.franchise_product_prices' not in lowered


def test_migration_0007_is_unchanged_and_still_has_old_comparisons():
    assert MIGRATION_0007.exists()
    sql = MIGRATION_0007.read_text(encoding='utf-8')
    lowered = sql.lower()
    assert 'new.selling_price >= v_master' in lowered
    assert 'fpp.selling_price >= new.price' in lowered
    assert 'Selling price must be strictly less than the master price' in sql


def test_validate_selling_price_below_master_passes():
    validate_selling_price(99, 100)
    validate_selling_price('0.01', 100)


def test_validate_selling_price_equal_to_master_passes():
    validate_selling_price(100, 100)
    validate_selling_price('100.00', 100)


def test_validate_selling_price_above_master_fails():
    with pytest.raises(HTTPException) as exc:
        validate_selling_price(101, 100)
    assert exc.value.status_code == 400
    assert exc.value.detail == SELLING_PRICE_EXCEEDS_MASTER


def test_validate_selling_price_zero_fails():
    with pytest.raises(HTTPException) as exc:
        validate_selling_price(0, 100)
    assert exc.value.status_code == 400
    assert exc.value.detail == SELLING_PRICE_NOT_POSITIVE


def test_validate_selling_price_negative_fails():
    with pytest.raises(HTTPException) as exc:
        validate_selling_price(-1, 100)
    assert exc.value.status_code == 400
    assert exc.value.detail == SELLING_PRICE_NOT_POSITIVE


def test_selling_price_equal_to_master_does_not_conflict():
    assert selling_price_conflicts_with_master([100], 100) is False
    assert selling_price_conflicts_with_master([101], 100) is True
    assert selling_price_conflicts_with_master([99], 100) is False


def test_admin_assign_selling_price_rule(client, auth_header_factory):
    product = _create_priced_product(
        client, auth_header_factory, name='Assign Price Rule Stick', master=100
    )

    below = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 99, 'is_active': True},
    )
    assert below.status_code == 201
    assert below.json()['selling_price'] == 99

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
        json={'selling_price': 101},
    )
    assert above.status_code == 400
    assert above.json()['detail'] == SELLING_PRICE_EXCEEDS_MASTER

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

    still = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
    )
    item = next(i for i in still.json()['items'] if i['product_id'] == product['id'])
    assert item['selling_price'] == 100


def test_admin_create_assignment_rejects_above_zero_and_negative(client, auth_header_factory):
    product = _create_priced_product(
        client, auth_header_factory, name='Create Price Rule Stick', master=100
    )

    above = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 101, 'is_active': True},
    )
    assert above.status_code == 400
    assert above.json()['detail'] == SELLING_PRICE_EXCEEDS_MASTER

    zero = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 0, 'is_active': True},
    )
    assert zero.status_code in {400, 422}

    negative = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': -1, 'is_active': True},
    )
    assert negative.status_code in {400, 422}

    equal = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
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
        json={'selling_price': 99},
    )
    assert below.status_code == 200
    assert below.json()['selling_price'] == 99

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
        json={'selling_price': 101},
    )
    assert above.status_code == 400
    assert above.json()['detail'] == SELLING_PRICE_EXCEEDS_MASTER

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
