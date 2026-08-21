"""M6.1 business-rule corrections: users, categories, owner pricing, POS, navigation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tests.conftest import (
    ADMIN_ID,
    CATEGORY_GARDEN,
    CATEGORY_ZEST,
    EMPLOYEE_ID,
    FRANCHISE_A,
    FRANCHISE_B,
    OWNER_CANDIDATE_ID,
    OWNER_ID,
    PRODUCT_NIMBU,
    PRODUCT_ORANGE,
)

MIGRATION_0007 = (
    Path(__file__).resolve().parents[2]
    / 'supabase'
    / 'migrations'
    / '0007_business_rules.sql'
)

MIGRATION_FAIL_MESSAGE = (
    '0007 cannot be applied: existing franchise selling prices are greater '
    'than or equal to their product master prices. Correct these pricing '
    'records before applying this migration.'
)


def _admin(auth_header_factory):
    return auth_header_factory(ADMIN_ID, 'admin@realstick.in')


def _owner(auth_header_factory):
    return auth_header_factory(OWNER_ID, 'owner@realstick.in')


def _employee(auth_header_factory):
    return auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in')


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


def _migration_0007_preflight(tables: dict) -> None:
    """Mirror 0007's conflict check: fail without mutating prices."""
    products = {str(row['id']): row for row in tables.get('products', [])}
    for assignment in tables.get('franchise_product_prices', []):
        product = products.get(str(assignment.get('product_id')))
        if not product:
            continue
        selling = float(assignment['selling_price'])
        master = float(product['price'])
        if selling >= master:
            raise RuntimeError(MIGRATION_FAIL_MESSAGE)
        if selling <= 0:
            raise RuntimeError(
                '0007 cannot be applied: existing franchise selling prices must be greater than 0. '
                'Correct these pricing records before applying this migration.'
            )


# ── Migration 0007 data-validation ──────────────────────────────────────────


def test_migration_0007_exists_and_does_not_rewrite_prices():
    assert MIGRATION_0007.exists()
    sql = MIGRATION_0007.read_text(encoding='utf-8')
    lowered = sql.lower()
    assert 'max_selling + 1' not in lowered
    assert 'price = sub.max_selling' not in lowered
    assert 'set\n  price = sub.max_selling' not in lowered
    assert 'p.price = sub.max_selling' not in lowered
    assert 'update public.products p' not in lowered
    assert 'update public.franchise_product_prices' not in lowered
    assert 'delete from public.products' not in lowered
    assert 'delete from public.franchise_product_prices' not in lowered
    assert 'delete from public.orders' not in lowered
    assert 'drop table' not in lowered
    assert 'franchise_applications' not in lowered or 'drop table if exists public.franchise_applications' not in lowered
    assert MIGRATION_FAIL_MESSAGE in ' '.join(sql.split())
    assert '0 < selling_price < products.price' in sql
    assert 'set_product_category_active' in sql
    assert 'and is_active is true' in sql
    assert 'POS_ERROR:INACTIVE_CATEGORY' in sql
    assert 'if p_is_active is not true then' in lowered


def test_migration_0007_preflight_does_not_change_master_or_selling_prices(fake_db):
    product = next(row for row in fake_db.tables['products'] if row['id'] == str(PRODUCT_NIMBU))
    assignment = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    product['price'] = 20
    assignment['selling_price'] = 22
    products_before = deepcopy(fake_db.tables['products'])
    assignments_before = deepcopy(fake_db.tables['franchise_product_prices'])

    try:
        _migration_0007_preflight(fake_db.tables)
        raise AssertionError('preflight should fail when selling_price >= master price')
    except RuntimeError as exc:
        assert 'cannot be applied' in str(exc)
        assert 'greater than or equal' in str(exc)

    assert fake_db.tables['products'] == products_before
    assert fake_db.tables['franchise_product_prices'] == assignments_before
    assert float(product['price']) == 20
    assert float(assignment['selling_price']) == 22


def test_migration_0007_preflight_allows_valid_existing_prices(fake_db):
    products_before = deepcopy(fake_db.tables['products'])
    assignments_before = deepcopy(fake_db.tables['franchise_product_prices'])
    _migration_0007_preflight(fake_db.tables)
    assert fake_db.tables['products'] == products_before
    assert fake_db.tables['franchise_product_prices'] == assignments_before


# ── User management ─────────────────────────────────────────────────────────


def test_admin_user_list_contains_admins_and_owners_only(client, auth_header_factory):
    response = client.get('/api/v1/admin/users', headers=_admin(auth_header_factory))
    assert response.status_code == 200
    roles = {item['role'] for item in response.json()['items']}
    assert 'SYSTEM_ADMIN' in roles
    assert 'FRANCHISE_OWNER' in roles
    assert 'EMPLOYEE' not in roles
    assert all(item['id'] != str(EMPLOYEE_ID) for item in response.json()['items'])


def test_admin_employee_role_filter_returns_no_employees(client, auth_header_factory):
    response = client.get(
        '/api/v1/admin/users',
        headers=_admin(auth_header_factory),
        params={'role': 'EMPLOYEE'},
    )
    assert response.status_code == 200
    assert response.json()['items'] == []
    assert response.json()['total'] == 0


def test_admin_cannot_create_employee(client, auth_header_factory):
    response = client.post(
        '/api/v1/admin/users',
        headers=_admin(auth_header_factory),
        json={
            'full_name': 'Admin Created Employee',
            'email': 'admin.created.employee@realstick.in',
            'role': 'EMPLOYEE',
            'franchise_id': str(FRANCHISE_A),
        },
    )
    assert response.status_code == 422


def test_admin_cannot_get_update_or_reset_employee(client, auth_header_factory):
    headers = _admin(auth_header_factory)
    assert client.get(f'/api/v1/admin/users/{EMPLOYEE_ID}', headers=headers).status_code == 404
    assert (
        client.patch(
            f'/api/v1/admin/users/{EMPLOYEE_ID}',
            headers=headers,
            json={'is_active': False},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f'/api/v1/admin/users/{EMPLOYEE_ID}/reset-password',
            headers=headers,
        ).status_code
        == 404
    )


def test_owner_employee_scope_and_limit_remain(client, auth_header_factory):
    listed = client.get('/api/v1/owner/employees', headers=_owner(auth_header_factory))
    assert listed.status_code == 200
    body = listed.json()
    assert all(item['franchise_id'] == str(FRANCHISE_A) for item in body['items'])
    assert all(item['id'] != str(OWNER_CANDIDATE_ID) for item in body['items'])
    assert body['employee_limit'] == 10

    created = client.post(
        '/api/v1/owner/employees',
        headers=_owner(auth_header_factory),
        json={'full_name': 'M61 Hire', 'login_id': 'EMPM61', 'password': 'TestPass12'},
    )
    assert created.status_code == 201
    employee_id = created.json()['user']['id']
    deactivated = client.patch(
        f'/api/v1/owner/employees/{employee_id}',
        headers=_owner(auth_header_factory),
        json={'is_active': False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()['is_active'] is False


# ── Category deactivation ───────────────────────────────────────────────────


def test_deactivating_category_deactivates_products_and_keeps_assignments(
    client, auth_header_factory, fake_db
):
    assignment_before = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    selling_before = assignment_before['selling_price']
    assignment_id = assignment_before['id']

    response = client.patch(
        f'/api/v1/admin/product-categories/{CATEGORY_ZEST}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert response.status_code == 200
    assert response.json()['is_active'] is False

    product = client.get(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
    ).json()
    assert product['is_active'] is False
    assert product['category_id'] == str(CATEGORY_ZEST)

    assignment_after = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    assert assignment_after['id'] == assignment_id
    assert assignment_after['selling_price'] == selling_before
    assert assignment_after['is_active'] is True

    menu = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory)).json()
    assert all(item['product_id'] != str(PRODUCT_NIMBU) for item in menu['items'])
    checkout = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 1}], 'payment_method': 'UPI'},
    )
    assert checkout.status_code == 400


def test_reactivating_category_does_not_reactivate_products(client, auth_header_factory):
    client.patch(
        f'/api/v1/admin/product-categories/{CATEGORY_ZEST}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    client.patch(
        f'/api/v1/admin/product-categories/{CATEGORY_ZEST}',
        headers=_admin(auth_header_factory),
        json={'is_active': True},
    )
    product = client.get(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
    ).json()
    assert product['is_active'] is False
    category = client.get(
        '/api/v1/admin/product-categories',
        headers=_admin(auth_header_factory),
    ).json()
    zest = next(item for item in category['items'] if item['id'] == str(CATEGORY_ZEST))
    assert zest['is_active'] is True

    menu = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory)).json()
    assert all(item['product_id'] != str(PRODUCT_NIMBU) for item in menu['items'])
    checkout = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 1}], 'payment_method': 'CASH'},
    )
    assert checkout.status_code == 400

    reactivated = client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': True},
    )
    assert reactivated.status_code == 200
    assert reactivated.json()['is_active'] is True
    menu_after = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory)).json()
    assert any(item['product_id'] == str(PRODUCT_NIMBU) for item in menu_after['items'])


def test_category_deactivation_is_atomic(client, auth_header_factory, fake_db):
    fake_db.fail_next_set_category_active = True
    before_category = next(
        row for row in fake_db.tables['product_categories'] if row['id'] == str(CATEGORY_ZEST)
    )
    before_product = next(row for row in fake_db.tables['products'] if row['id'] == str(PRODUCT_NIMBU))
    response = client.patch(
        f'/api/v1/admin/product-categories/{CATEGORY_ZEST}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert response.status_code == 503
    after_category = next(
        row for row in fake_db.tables['product_categories'] if row['id'] == str(CATEGORY_ZEST)
    )
    after_product = next(row for row in fake_db.tables['products'] if row['id'] == str(PRODUCT_NIMBU))
    assert after_category['is_active'] == before_category['is_active']
    assert after_product['is_active'] == before_product['is_active']


# ── Product authorization ───────────────────────────────────────────────────


def test_admin_can_activate_deactivate_products(client, auth_header_factory):
    hidden = client.patch(
        f'/api/v1/admin/products/{PRODUCT_ORANGE}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert hidden.status_code == 200
    assert hidden.json()['is_active'] is False
    shown = client.patch(
        f'/api/v1/admin/products/{PRODUCT_ORANGE}',
        headers=_admin(auth_header_factory),
        json={'is_active': True},
    )
    assert shown.status_code == 200
    assert shown.json()['is_active'] is True


def test_owner_and_employee_cannot_modify_product_master_fields(client, auth_header_factory):
    for headers in (_owner(auth_header_factory), _employee(auth_header_factory)):
        assert (
            client.patch(
                f'/api/v1/admin/products/{PRODUCT_NIMBU}',
                headers=headers,
                json={'is_active': False},
            ).status_code
            == 403
        )
        assert (
            client.patch(
                f'/api/v1/admin/products/{PRODUCT_NIMBU}',
                headers=headers,
                json={'name': 'Hacked', 'price': 1, 'category_id': str(CATEGORY_GARDEN)},
            ).status_code
            == 403
        )


def test_owner_cannot_activate_or_deactivate_via_menu_api(client, auth_header_factory, fake_db):
    for payload in (
        {'is_active': False},
        {'is_active': True},
        {'selling_price': 80, 'is_active': False},
        {'available_for_pos': True},
        {'product_id': str(PRODUCT_ORANGE)},
        {'franchise_id': str(FRANCHISE_B)},
    ):
        response = client.patch(
            f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
            headers=_owner(auth_header_factory),
            json=payload,
        )
        assert response.status_code == 422, payload
    assignment = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    assert assignment['is_active'] is True
    assert assignment['franchise_id'] == str(FRANCHISE_A)


# ── Pricing ─────────────────────────────────────────────────────────────────


def test_selling_price_must_be_positive_and_independent_of_master(client, auth_header_factory):
    product = _create_priced_product(client, auth_header_factory, name='Master 100 Stick', master=100)
    assigned = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 90, 'is_active': True},
    )
    assert assigned.status_code == 201
    assert assigned.json()['selling_price'] == 90
    assert assigned.json()['master_price'] == 100

    assert (
        client.patch(
            f'/api/v1/owner/menu/{product["id"]}',
            headers=_owner(auth_header_factory),
            json={'selling_price': 80},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f'/api/v1/owner/menu/{product["id"]}',
            headers=_owner(auth_header_factory),
            json={'selling_price': 95},
        ).status_code
        == 200
    )

    assert (
        client.patch(
            f'/api/v1/owner/menu/{product["id"]}',
            headers=_owner(auth_header_factory),
            json={'selling_price': 99.99},
        ).status_code
        == 200
    )

    assert (
        client.patch(
            f'/api/v1/owner/menu/{product["id"]}',
            headers=_owner(auth_header_factory),
            json={'selling_price': 100},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f'/api/v1/owner/menu/{product["id"]}',
            headers=_owner(auth_header_factory),
            json={'selling_price': 100.00},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f'/api/v1/owner/menu/{product["id"]}',
            headers=_owner(auth_header_factory),
            json={'selling_price': 120},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f'/api/v1/owner/menu/{product["id"]}',
            headers=_owner(auth_header_factory),
            json={'selling_price': 150},
        ).status_code
        == 200
    )

    for invalid in (0, -1, 99.999):
        response = client.patch(
            f'/api/v1/owner/menu/{product["id"]}',
            headers=_owner(auth_header_factory),
            json={'selling_price': invalid},
        )
        assert response.status_code in {400, 422}, invalid

    admin_above = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 101, 'is_active': True},
    )
    assert admin_above.status_code == 201
    assert admin_above.json()['selling_price'] == 101

    admin_equal = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products/{product["id"]}',
        headers=_admin(auth_header_factory),
        json={'selling_price': 100},
    )
    assert admin_equal.status_code == 200
    assert admin_equal.json()['selling_price'] == 100


def test_master_price_can_be_reduced_below_existing_selling_price(
    client, auth_header_factory, fake_db
):
    product = _create_priced_product(client, auth_header_factory, name='Conflict Stick', master=100)
    assigned = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={'product_id': product['id'], 'selling_price': 90, 'is_active': True},
    )
    assert assigned.status_code == 201

    reduced = client.patch(
        f'/api/v1/admin/products/{product["id"]}',
        headers=_admin(auth_header_factory),
        json={'price': 80},
    )
    assert reduced.status_code == 200
    assert reduced.json()['price'] == 80

    stored = next(row for row in fake_db.tables['products'] if row['id'] == product['id'])
    assert float(stored['price']) == 80
    assignment = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == product['id']
    )
    assert float(assignment['selling_price']) == 90

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
    assert float(still['selling_price']) == 90


# ── Owner pricing of inactive products ──────────────────────────────────────


def test_owner_can_edit_selling_price_of_active_product_and_assignment(
    client, auth_header_factory, fake_db
):
    menu = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    assert menu.status_code == 200
    item = next(i for i in menu.json()['items'] if i['product_id'] == str(PRODUCT_NIMBU))
    assert item['product_is_active'] is True
    assert item['is_active'] is True
    assert item['price_editable'] is True
    assert item['selling_price'] == 22

    updated = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 31.5},
    )
    assert updated.status_code == 200
    assert updated.json()['selling_price'] == 31.5
    assert updated.json()['price_editable'] is True
    assignment = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    assert float(assignment['selling_price']) == 31.5
    assert assignment['is_active'] is True


def test_owner_cannot_edit_selling_price_when_product_inactive(
    client, auth_header_factory, fake_db
):
    hidden = client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert hidden.status_code == 200
    assert hidden.json()['is_active'] is False

    menu = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    assert menu.status_code == 200
    item = next(i for i in menu.json()['items'] if i['product_id'] == str(PRODUCT_NIMBU))
    assert item['product_is_active'] is False
    assert item['is_active'] is True
    assert item['price_editable'] is False
    assert item['selling_price'] == 22

    rejected = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 40},
    )
    assert rejected.status_code == 409
    assert 'active' in rejected.json()['detail'].lower()
    assert 'product' in rejected.json()['detail'].lower()

    assignment = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    assert float(assignment['selling_price']) == 22
    product = next(row for row in fake_db.tables['products'] if row['id'] == str(PRODUCT_NIMBU))
    assert product['is_active'] is False


def test_owner_cannot_edit_selling_price_when_franchise_assignment_inactive(
    client, auth_header_factory, fake_db
):
    hidden = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert hidden.status_code == 200
    assert hidden.json()['is_active'] is False

    menu = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    assert menu.status_code == 200
    item = next(i for i in menu.json()['items'] if i['product_id'] == str(PRODUCT_NIMBU))
    assert item['product_is_active'] is True
    assert item['is_active'] is False
    assert item['price_editable'] is False
    assert item['selling_price'] == 22

    rejected = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 40},
    )
    assert rejected.status_code == 409
    assert 'assignment' in rejected.json()['detail'].lower()

    assignment = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    assert float(assignment['selling_price']) == 22
    assert assignment['is_active'] is False


def test_owner_cannot_activate_or_deactivate_product(client, auth_header_factory, fake_db):
    before = next(row for row in fake_db.tables['products'] if row['id'] == str(PRODUCT_NIMBU))
    assert before['is_active'] is True

    forbidden = client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'is_active': False},
    )
    assert forbidden.status_code == 403

    menu_toggle = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'is_active': False},
    )
    assert menu_toggle.status_code == 422

    after = next(row for row in fake_db.tables['products'] if row['id'] == str(PRODUCT_NIMBU))
    assert after['is_active'] is True


def test_owner_cannot_activate_or_deactivate_franchise_assignment(
    client, auth_header_factory, fake_db
):
    assignment_before = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    assert assignment_before['is_active'] is True

    for payload in (
        {'is_active': False},
        {'is_active': True},
        {'selling_price': 33, 'is_active': False},
    ):
        response = client.patch(
            f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
            headers=_owner(auth_header_factory),
            json=payload,
        )
        assert response.status_code == 422, payload

    admin_endpoint = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'is_active': False},
    )
    assert admin_endpoint.status_code == 403

    assignment_after = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    assert assignment_after['is_active'] is True
    assert float(assignment_after['selling_price']) == 22


def test_employee_pos_does_not_show_inactive_products(client, auth_header_factory):
    visible = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory))
    assert visible.status_code == 200
    assert any(item['product_id'] == str(PRODUCT_NIMBU) for item in visible.json()['items'])

    client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    hidden_product = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory))
    assert all(item['product_id'] != str(PRODUCT_NIMBU) for item in hidden_product.json()['items'])

    owner_view = client.get('/api/v1/owner/menu', headers=_owner(auth_header_factory))
    assert any(item['product_id'] == str(PRODUCT_NIMBU) for item in owner_view.json()['items'])

    client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': True},
    )
    client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    hidden_assignment = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory))
    assert all(
        item['product_id'] != str(PRODUCT_NIMBU) for item in hidden_assignment.json()['items']
    )


def test_admin_can_still_edit_selling_price_of_inactive_assignment(
    client, auth_header_factory, fake_db
):
    client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    updated = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'selling_price': 18},
    )
    assert updated.status_code == 200
    assert updated.json()['selling_price'] == 18
    assert updated.json()['is_active'] is False
    assignment = next(
        row
        for row in fake_db.tables['franchise_product_prices']
        if row['product_id'] == str(PRODUCT_NIMBU)
    )
    assert float(assignment['selling_price']) == 18


def test_owner_existing_valid_pricing_still_works(client, auth_header_factory):
    valid = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 27},
    )
    assert valid.status_code == 200
    assert valid.json()['selling_price'] == 27
    assert valid.json()['master_price'] == 100

    at_master = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 100},
    )
    assert at_master.status_code == 200
    assert at_master.json()['selling_price'] == 100

    above_master = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 101},
    )
    assert above_master.status_code == 200
    assert above_master.json()['selling_price'] == 101

    zero = client.patch(
        f'/api/v1/owner/menu/{PRODUCT_NIMBU}',
        headers=_owner(auth_header_factory),
        json={'selling_price': 0},
    )
    assert zero.status_code in {400, 422}


# ── POS availability ────────────────────────────────────────────────────────


def test_pos_requires_product_category_and_assignment_active(client, auth_header_factory):
    menu = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory)).json()
    assert any(item['product_id'] == str(PRODUCT_NIMBU) for item in menu['items'])
    assert all(item['available_for_pos'] is True for item in menu['items'])

    client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    hidden_product = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory)).json()
    assert all(item['product_id'] != str(PRODUCT_NIMBU) for item in hidden_product['items'])
    client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': True},
    )

    client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    hidden_assignment = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory)).json()
    assert all(item['product_id'] != str(PRODUCT_NIMBU) for item in hidden_assignment['items'])
    checkout = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 1}], 'payment_method': 'UPI'},
    )
    assert checkout.status_code == 400


def test_inactive_category_blocks_pos_even_if_product_active(client, auth_header_factory, fake_db):
    zest = next(row for row in fake_db.tables['product_categories'] if row['id'] == str(CATEGORY_ZEST))
    zest['is_active'] = False
    menu = client.get('/api/v1/pos/menu', headers=_employee(auth_header_factory)).json()
    assert all(item['product_id'] != str(PRODUCT_NIMBU) for item in menu['items'])
    checkout = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 1}], 'payment_method': 'CARD'},
    )
    assert checkout.status_code == 400


def test_employee_still_logs_in_and_owner_can_reset_password(client, auth_header_factory, fake_db):
    me = client.get('/api/v1/auth/me', headers=_employee(auth_header_factory))
    assert me.status_code == 200
    assert me.json()['role'] == 'EMPLOYEE'
    reset = client.post(
        f'/api/v1/owner/employees/{EMPLOYEE_ID}/reset-password',
        headers=_owner(auth_header_factory),
        json={'new_password': 'kept-backend-reset-99', 'confirm_password': 'kept-backend-reset-99'},
    )
    assert reset.status_code == 200
    assert reset.json()['password_setup'] == 'password_set'
    assert not fake_db.auth.recovery_emails

    own_password = client.post(
        '/api/v1/auth/change-password',
        headers=_employee(auth_header_factory),
        json={'new_password': 'kept-backend-reset-99'},
    )
    assert own_password.status_code == 403
