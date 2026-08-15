"""Franchise Owner menu and selling-price tests (M4B.1)."""

from __future__ import annotations

from tests.conftest import (
    ADMIN_ID,
    EMPLOYEE_ID,
    FRANCHISE_A,
    FRANCHISE_B,
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


def _assign_orange_to_franchise_b(client, auth_header_factory, selling_price: float = 45):
    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
        json={
            'product_id': str(PRODUCT_ORANGE),
            'selling_price': selling_price,
            'is_active': True,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_owner_can_list_own_franchise_menu(client, auth_header_factory):
    response = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['total'] >= 1
    assert all(item['franchise_id'] == str(FRANCHISE_A) for item in body['items'])


def test_owner_sees_assigned_products(client, auth_header_factory):
    response = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    assert response.status_code == 200
    ids = {item['product_id'] for item in response.json()['items']}
    assert str(PRODUCT_NIMBU) in ids


def test_owner_does_not_see_unassigned_products(client, auth_header_factory):
    _assign_orange_to_franchise_b(client, auth_header_factory)
    response = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    assert response.status_code == 200
    ids = {item['product_id'] for item in response.json()['items']}
    assert str(PRODUCT_NIMBU) in ids
    assert str(PRODUCT_ORANGE) not in ids


def test_owner_sees_correct_franchise_selling_price(client, auth_header_factory):
    response = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    item = next(i for i in response.json()['items'] if i['product_id'] == str(PRODUCT_NIMBU))
    assert item['selling_price'] == 22
    assert item['master_price'] == 100
    assert item['product_name'] == 'Nimbu Pudina'
    assert item['category_name'] == 'Zest Collection'
    assert item['available_for_pos'] is True
    assert item['price_editable'] is True


def test_owner_can_update_own_franchise_price(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 30.5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['selling_price'] == 30.5
    assert body['franchise_id'] == str(FRANCHISE_A)
    assert body['master_price'] == 100

    listed = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    item = next(i for i in listed.json()['items'] if i['product_id'] == str(PRODUCT_NIMBU))
    assert item['selling_price'] == 30.5


def test_owner_cannot_modify_master_product_price(client, auth_header_factory, fake_db):
    before = next(p for p in fake_db.tables['products'] if p['id'] == str(PRODUCT_NIMBU))
    assert before['price'] == 100

    response = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 35, 'price': 999},
    )
    assert response.status_code == 422

    valid = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 35},
    )
    assert valid.status_code == 200
    assert valid.json()['selling_price'] == 35
    assert valid.json()['master_price'] == 100

    after = next(p for p in fake_db.tables['products'] if p['id'] == str(PRODUCT_NIMBU))
    assert after['price'] == 100

    admin_product = client.get(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
    )
    assert admin_product.status_code == 200
    assert admin_product.json()['price'] == 100

    forbidden = client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'price': 99},
    )
    assert forbidden.status_code == 403


def test_owner_cannot_access_another_franchise_menu(client, auth_header_factory):
    _assign_orange_to_franchise_b(client, auth_header_factory, selling_price=48)

    listed = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    assert listed.status_code == 200
    body = listed.json()
    assert all(item['franchise_id'] == str(FRANCHISE_A) for item in body['items'])
    assert all(item['product_id'] != str(PRODUCT_ORANGE) for item in body['items'])

    admin_other = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_owner(auth_header_factory),
    )
    assert admin_other.status_code == 403


def test_owner_cannot_update_another_franchise_price(client, auth_header_factory):
    assigned = _assign_orange_to_franchise_b(client, auth_header_factory, selling_price=48)
    assert assigned['selling_price'] == 48

    response = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_ORANGE}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 1},
    )
    assert response.status_code == 403

    admin_other = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products/{PRODUCT_ORANGE}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 1},
    )
    assert admin_other.status_code == 403

    still = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
    )
    item = next(i for i in still.json()['items'] if i['product_id'] == str(PRODUCT_ORANGE))
    assert item['selling_price'] == 48


def test_employee_cannot_access_owner_menu(client, auth_header_factory):
    listed = client.get('/api/v1/owner/menu', headers=_employee(auth_header_factory))
    assert listed.status_code == 403

    patched = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_employee(auth_header_factory),
        json={'selling_price': 99},
    )
    assert patched.status_code == 403


def test_admin_cannot_use_owner_menu_endpoints(client, auth_header_factory):
    listed = client.get('/api/v1/owner/menu', headers=_admin(auth_header_factory))
    assert listed.status_code == 403

    patched = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'selling_price': 99},
    )
    assert patched.status_code == 403


def test_admin_franchise_pricing_still_works(client, auth_header_factory):
    listed = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
    )
    assert listed.status_code == 200
    item = next(i for i in listed.json()['items'] if i['product_id'] == str(PRODUCT_NIMBU))
    assert item['selling_price'] == 22

    patched = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'selling_price': 26},
    )
    assert patched.status_code == 200
    assert patched.json()['selling_price'] == 26
    assert patched.json()['master_price'] == 100

    owner_view = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    owner_item = next(
        i for i in owner_view.json()['items'] if i['product_id'] == str(PRODUCT_NIMBU)
    )
    assert owner_item['selling_price'] == 26


def test_owner_cannot_toggle_franchise_availability(client, auth_header_factory, fake_db):
    hidden = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'is_active': False},
    )
    assert hidden.status_code == 422
    assignment = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    assert assignment['is_active'] is True

    shown = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 22, 'is_active': False},
    )
    assert shown.status_code == 422
    assignment = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    assert assignment['is_active'] is True


def test_owner_can_view_but_not_price_inactive_product(client, auth_header_factory, fake_db):
    client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    listed = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    assert listed.status_code == 200
    item = next(i for i in listed.json()['items'] if i['product_id'] == str(PRODUCT_NIMBU))
    assert item['price_editable'] is False
    assert item['selling_price'] == 22

    rejected = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 40},
    )
    assert rejected.status_code == 409
    assignment = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    assert float(assignment['selling_price']) == 22


def test_owner_price_validation_rejects_invalid_values(client, auth_header_factory):
    negative = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': -1},
    )
    assert negative.status_code == 422

    too_precise = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 22.999},
    )
    assert too_precise.status_code == 422

    empty = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={},
    )
    assert empty.status_code == 422
