"""Dynamic product category management tests."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.modules.products.constants import INITIAL_PRODUCT_CATEGORIES
from tests.conftest import (
    ADMIN_ID,
    CATEGORY_GARDEN,
    CATEGORY_HARVEST,
    CATEGORY_KULFI,
    CATEGORY_RESERVE,
    CATEGORY_ROGUE,
    CATEGORY_ZEST,
    EMPLOYEE_ID,
    OWNER_ID,
    PRODUCT_NIMBU,
)

MIGRATION_0002 = (
    Path(__file__).resolve().parents[2]
    / 'supabase'
    / 'migrations'
    / '0002_seed_fixed_product_categories.sql'
)

INITIAL_CATEGORY_IDS = [
    CATEGORY_ZEST,
    CATEGORY_GARDEN,
    CATEGORY_HARVEST,
    CATEGORY_RESERVE,
    CATEGORY_KULFI,
]


def _admin(auth_header_factory):
    return auth_header_factory(ADMIN_ID, 'admin@realstick.in')


def _owner(auth_header_factory):
    return auth_header_factory(OWNER_ID, 'owner@realstick.in')


def _employee(auth_header_factory):
    return auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in')


def test_migration_0002_seeds_initial_five_categories():
    assert MIGRATION_0002.exists()
    sql = MIGRATION_0002.read_text(encoding='utf-8')
    assert 'on conflict (name) do nothing' in sql.lower()
    for name in INITIAL_PRODUCT_CATEGORIES:
        assert name in sql


def test_initial_five_categories_exist(client, auth_header_factory):
    response = client.get('/api/v1/admin/product-categories', headers=_admin(auth_header_factory))
    assert response.status_code == 200
    names = {item['name'] for item in response.json()['items']}
    for name in INITIAL_PRODUCT_CATEGORIES:
        assert name in names


def test_admin_can_list_categories(client, auth_header_factory):
    response = client.get('/api/v1/admin/product-categories', headers=_admin(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['total'] >= 5
    assert len(body['items']) == body['total']


def test_admin_can_create_additional_categories(client, auth_header_factory):
    first = client.post(
        '/api/v1/admin/product-categories',
        headers=_admin(auth_header_factory),
        json={'name': 'Summer Specials', 'display_order': 10, 'is_active': True},
    )
    assert first.status_code == 201
    assert first.json()['name'] == 'Summer Specials'

    second = client.post(
        '/api/v1/admin/product-categories',
        headers=_admin(auth_header_factory),
        json={'name': 'Premium Collection', 'display_order': 11, 'is_active': True},
    )
    assert second.status_code == 201
    assert second.json()['name'] == 'Premium Collection'

    listed = client.get('/api/v1/admin/product-categories', headers=_admin(auth_header_factory))
    names = {item['name'] for item in listed.json()['items']}
    assert 'Summer Specials' in names
    assert 'Premium Collection' in names


def test_duplicate_category_name_rejected(client, auth_header_factory):
    response = client.post(
        '/api/v1/admin/product-categories',
        headers=_admin(auth_header_factory),
        json={'name': 'Zest Collection', 'display_order': 99},
    )
    assert response.status_code == 409


def test_duplicate_category_name_case_insensitive(client, auth_header_factory):
    response = client.post(
        '/api/v1/admin/product-categories',
        headers=_admin(auth_header_factory),
        json={'name': 'zest collection', 'display_order': 99},
    )
    assert response.status_code == 409


def test_blank_category_name_rejected(client, auth_header_factory):
    response = client.post(
        '/api/v1/admin/product-categories',
        headers=_admin(auth_header_factory),
        json={'name': '   ', 'display_order': 1},
    )
    assert response.status_code == 422


def test_admin_can_edit_category(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/admin/product-categories/{CATEGORY_GARDEN}',
        headers=_admin(auth_header_factory),
        json={'display_order': 20, 'name': 'Garden Collection'},
    )
    assert response.status_code == 200
    assert response.json()['display_order'] == 20


def test_admin_can_deactivate_category(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/admin/product-categories/{CATEGORY_KULFI}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert response.status_code == 200
    assert response.json()['is_active'] is False


def test_inactive_category_cannot_be_assigned_to_new_product(client, auth_header_factory):
    client.patch(
        f'/api/v1/admin/product-categories/{CATEGORY_RESERVE}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    response = client.post(
        '/api/v1/admin/products',
        headers=_admin(auth_header_factory),
        json={
            'name': 'Should Fail',
            'category_id': str(CATEGORY_RESERVE),
            'price': 70,
        },
    )
    assert response.status_code == 400
    assert 'inactive' in response.json()['detail'].lower()


def test_existing_product_remains_with_inactive_category(client, auth_header_factory):
    client.patch(
        f'/api/v1/admin/product-categories/{CATEGORY_ZEST}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    response = client.get(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
    )
    assert response.status_code == 200
    assert response.json()['category_id'] == str(CATEGORY_ZEST)
    assert response.json()['name'] == 'Nimbu Pudina'
    assert response.json()['is_active'] is False

    # Updating non-category fields still works while category is inactive
    patch = client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'description': 'Still on inactive category'},
    )
    assert patch.status_code == 200
    assert patch.json()['category_id'] == str(CATEGORY_ZEST)


def test_category_referenced_by_products_cannot_be_deleted(client, auth_header_factory):
    response = client.delete(
        f'/api/v1/admin/product-categories/{CATEGORY_ZEST}',
        headers=_admin(auth_header_factory),
    )
    assert response.status_code == 409
    assert 'referenced' in response.json()['detail'].lower()


def test_unused_category_can_be_deleted(client, auth_header_factory):
    # CATEGORY_ROGUE has no products in fixtures
    response = client.delete(
        f'/api/v1/admin/product-categories/{CATEGORY_ROGUE}',
        headers=_admin(auth_header_factory),
    )
    assert response.status_code == 204


def test_non_admin_cannot_manage_categories(client, auth_header_factory):
    for headers in (_owner(auth_header_factory), _employee(auth_header_factory)):
        create = client.post(
            '/api/v1/admin/product-categories',
            headers=headers,
            json={'name': 'Nope', 'display_order': 1},
        )
        assert create.status_code == 403

        update = client.patch(
            f'/api/v1/admin/product-categories/{CATEGORY_ZEST}',
            headers=headers,
            json={'is_active': False},
        )
        assert update.status_code == 403

        deactivate = client.patch(
            f'/api/v1/admin/product-categories/{CATEGORY_GARDEN}',
            headers=headers,
            json={'is_active': False},
        )
        assert deactivate.status_code == 403


def test_product_creation_works_with_any_active_category(client, auth_header_factory):
    created_cat = client.post(
        '/api/v1/admin/product-categories',
        headers=_admin(auth_header_factory),
        json={'name': 'Limited Edition', 'display_order': 50, 'is_active': True},
    )
    assert created_cat.status_code == 201
    category_id = created_cat.json()['id']

    product = client.post(
        '/api/v1/admin/products',
        headers=_admin(auth_header_factory),
        json={
            'name': 'Special Stick',
            'category_id': category_id,
            'price': 90,
        },
    )
    assert product.status_code == 201
    assert product.json()['category_id'] == category_id


def test_product_creation_rejects_unknown_category(client, auth_header_factory):
    response = client.post(
        '/api/v1/admin/products',
        headers=_admin(auth_header_factory),
        json={
            'name': 'Unknown Cat',
            'category_id': str(uuid4()),
            'price': 10,
        },
    )
    assert response.status_code == 400
    assert 'not found' in response.json()['detail'].lower()


def test_product_update_rejects_inactive_category_reassignment(client, auth_header_factory):
    client.patch(
        f'/api/v1/admin/product-categories/{CATEGORY_HARVEST}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    response = client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'category_id': str(CATEGORY_HARVEST)},
    )
    assert response.status_code == 400
    assert 'inactive' in response.json()['detail'].lower()


def test_product_creation_succeeds_for_each_initial_category(client, auth_header_factory):
    for index, category_id in enumerate(INITIAL_CATEGORY_IDS):
        response = client.post(
            '/api/v1/admin/products',
            headers=_admin(auth_header_factory),
            json={
                'name': f'Initial Cat Item {index}',
                'category_id': str(category_id),
                'price': 10 + index,
            },
        )
        assert response.status_code == 201, response.text
