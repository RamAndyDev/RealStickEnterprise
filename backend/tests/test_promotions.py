from datetime import datetime, timedelta, timezone

from tests.conftest import FRANCHISE_A, FRANCHISE_B, PRODUCT_NIMBU


def _admin(auth_header_factory):
    from tests.conftest import ADMIN_ID

    return auth_header_factory(ADMIN_ID, 'admin@realstick.in')


def _owner(auth_header_factory):
    from tests.conftest import OWNER_ID

    return auth_header_factory(OWNER_ID, 'owner@realstick.in')


def _employee(auth_header_factory):
    from tests.conftest import EMPLOYEE_ID

    return auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in')


def _create_promotion(client, auth_header_factory, **overrides):
    payload = {
        'name': 'Summer 26',
        'description': 'Seasonal campaign',
        'promo_code': 'SUMMER26',
        'is_active': True,
        'franchise_ids': [str(FRANCHISE_A)],
    }
    payload.update(overrides)
    return client.post('/api/v1/admin/promotions', headers=_admin(auth_header_factory), json=payload)


def test_admin_can_create_and_assign_promotion(client, auth_header_factory):
    response = _create_promotion(client, auth_header_factory)
    assert response.status_code == 201
    body = response.json()
    assert body['promo_code'] == 'SUMMER26'
    assert body['franchise_ids'] == [str(FRANCHISE_A)]


def test_admin_can_deactivate_promotion(client, auth_header_factory):
    created = _create_promotion(client, auth_header_factory).json()
    response = client.patch(
        f'/api/v1/admin/promotions/{created["id"]}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert response.status_code == 200
    assert response.json()['is_active'] is False


def test_owner_sees_applicable_promotions_only(client, auth_header_factory):
    _create_promotion(client, auth_header_factory)
    _create_promotion(
        client,
        auth_header_factory,
        name='Other',
        promo_code='OTHER26',
        franchise_ids=[str(FRANCHISE_B)],
    )
    response = client.get('/api/v1/owner/promotions', headers=_owner(auth_header_factory))
    assert response.status_code == 200
    codes = {item['promo_code'] for item in response.json()['items']}
    assert 'SUMMER26' in codes
    assert 'OTHER26' not in codes


def test_owner_can_create_local_and_linked_offers(client, auth_header_factory):
    promotion = _create_promotion(client, auth_header_factory).json()
    local = client.post(
        '/api/v1/owner/offers',
        headers=_owner(auth_header_factory),
        json={'name': 'Evening Special', 'discount_value': 15, 'is_active': True},
    )
    linked = client.post(
        '/api/v1/owner/offers',
        headers=_owner(auth_header_factory),
        json={
            'name': 'Summer Special',
            'discount_value': 10,
            'is_active': True,
            'promotion_id': promotion['id'],
        },
    )
    assert local.status_code == 201
    assert local.json()['promotion_id'] is None
    assert linked.status_code == 201
    assert linked.json()['promotion_id'] == promotion['id']


def test_owner_cannot_use_another_franchise_promotion(client, auth_header_factory):
    other = _create_promotion(
        client,
        auth_header_factory,
        promo_code='SEC26',
        franchise_ids=[str(FRANCHISE_B)],
    ).json()
    response = client.post(
        '/api/v1/owner/offers',
        headers=_owner(auth_header_factory),
        json={'name': 'Bad link', 'discount_value': 10, 'promotion_id': other['id']},
    )
    assert response.status_code == 403


def test_owner_cannot_modify_admin_promotion(client, auth_header_factory):
    created = _create_promotion(client, auth_header_factory).json()
    response = client.patch(
        f'/api/v1/admin/promotions/{created["id"]}',
        headers=_owner(auth_header_factory),
        json={'is_active': False},
    )
    assert response.status_code == 403


def test_linked_offer_hidden_when_promotion_inactive(client, auth_header_factory):
    promotion = _create_promotion(client, auth_header_factory).json()
    client.post(
        '/api/v1/owner/offers',
        headers=_owner(auth_header_factory),
        json={'name': 'Summer Special', 'discount_value': 10, 'promotion_id': promotion['id']},
    )
    client.post(
        '/api/v1/owner/offers',
        headers=_owner(auth_header_factory),
        json={'name': 'Evening Special', 'discount_value': 15},
    )
    before = {
        item['name']
        for item in client.get('/api/v1/pos/offers', headers=_employee(auth_header_factory)).json()['items']
    }
    assert 'Summer Special' in before
    assert 'Evening Special' in before
    client.patch(
        f'/api/v1/admin/promotions/{promotion["id"]}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    after = {
        item['name']
        for item in client.get('/api/v1/pos/offers', headers=_employee(auth_header_factory)).json()['items']
    }
    assert 'Summer Special' not in after
    assert 'Evening Special' in after


def test_linked_offer_hidden_after_promotion_expiry(client, auth_header_factory):
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    promotion = _create_promotion(
        client,
        auth_header_factory,
        promo_code='EXPIRED26',
        valid_to=yesterday,
    ).json()
    client.post(
        '/api/v1/owner/offers',
        headers=_owner(auth_header_factory),
        json={'name': 'Expired Link', 'discount_value': 10, 'promotion_id': promotion['id']},
    )
    names = {
        item['name']
        for item in client.get('/api/v1/pos/offers', headers=_employee(auth_header_factory)).json()['items']
    }
    assert 'Expired Link' not in names


def test_employee_cannot_apply_inactive_linked_offer(client, auth_header_factory):
    promotion = _create_promotion(client, auth_header_factory).json()
    offer = client.post(
        '/api/v1/owner/offers',
        headers=_owner(auth_header_factory),
        json={'name': 'Summer Special', 'discount_value': 10, 'promotion_id': promotion['id']},
    ).json()
    client.patch(
        f'/api/v1/admin/promotions/{promotion["id"]}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    checkout = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={
            'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 1}],
            'payment_method': 'CASH',
            'offer_id': offer['id'],
        },
    )
    assert checkout.status_code == 422


def test_employee_cannot_use_another_franchise_offer(client, auth_header_factory):
    created = client.post(
        '/api/v1/admin/offers',
        headers=_admin(auth_header_factory),
        json={
            'name': 'Secunderabad Only',
            'discount_value': 20,
            'franchise_id': str(FRANCHISE_B),
            'is_active': True,
        },
    )
    assert created.status_code == 201
    names = {
        item['name']
        for item in client.get('/api/v1/pos/offers', headers=_employee(auth_header_factory)).json()['items']
    }
    assert 'Secunderabad Only' not in names
    checkout = client.post(
        '/api/v1/pos/orders',
        headers=_employee(auth_header_factory),
        json={
            'items': [{'product_id': str(PRODUCT_NIMBU), 'quantity': 1}],
            'payment_method': 'CASH',
            'offer_id': created.json()['id'],
        },
    )
    assert checkout.status_code == 403


def test_public_has_no_promo_endpoint(client):
    assert client.get('/api/v1/public/promotions').status_code == 404
    assert client.get('/api/v1/public/offers').status_code == 404
    assert client.post('/api/v1/public/coupons', json={'code': 'SUMMER26'}).status_code == 404
