"""System Admin products, fixed categories, images, and franchise pricing tests."""

from __future__ import annotations

from io import BytesIO

from tests.conftest import (
    ADMIN_ID,
    CATEGORY_ZEST,
    EMPLOYEE_ID,
    FRANCHISE_A,
    FRANCHISE_B,
    OWNER_ID,
    PRODUCT_NIMBU,
    PRODUCT_ORANGE,
)

# Minimal valid image magic-byte payloads
JPEG_BYTES = b'\xff\xd8\xff\xe0' + b'\x00' * 64
PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64
WEBP_BYTES = b'RIFF' + (80).to_bytes(4, 'little') + b'WEBP' + b'\x00' * 64
GIF_BYTES = b'GIF89a' + b'\x00' * 64


def _admin(auth_header_factory):
    return auth_header_factory(ADMIN_ID, 'admin@realstick.in')


def _owner(auth_header_factory):
    return auth_header_factory(OWNER_ID, 'owner@realstick.in')


def _employee(auth_header_factory):
    return auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in')


def test_admin_can_list_products(client, auth_header_factory):
    response = client.get('/api/v1/admin/products', headers=_admin(auth_header_factory))
    assert response.status_code == 200
    body = response.json()
    assert body['total'] >= 2
    names = {item['name'] for item in body['items']}
    assert 'Nimbu Pudina' in names
    assert 'Nagpur Orange' in names


def test_admin_can_create_product(client, auth_header_factory):
    response = client.post(
        '/api/v1/admin/products',
        headers=_admin(auth_header_factory),
        json={
            'name': 'Pure Lemon',
            'category_id': str(CATEGORY_ZEST),
            'description': 'Just lemon. Just sugar.',
            'price': 20,
            'is_active': True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body['name'] == 'Pure Lemon'
    assert body['price'] == 20
    assert body['category_id'] == str(CATEGORY_ZEST)
    assert 'emoji' not in (body.get('metadata') or {})
    assert body['is_active'] is True


def test_admin_can_update_product(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'description': 'Lemon & garden mint', 'price': 25},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['description'] == 'Lemon & garden mint'
    assert body['price'] == 25


def test_admin_can_activate_deactivate_product(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/admin/products/{PRODUCT_ORANGE}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert response.status_code == 200
    assert response.json()['is_active'] is False

    response = client.patch(
        f'/api/v1/admin/products/{PRODUCT_ORANGE}',
        headers=_admin(auth_header_factory),
        json={'is_active': True},
    )
    assert response.status_code == 200
    assert response.json()['is_active'] is True


def test_admin_can_assign_product_to_franchise(client, auth_header_factory):
    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
        json={
            'product_id': str(PRODUCT_ORANGE),
            'selling_price': 45,
            'is_active': True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body['franchise_id'] == str(FRANCHISE_B)
    assert body['product_id'] == str(PRODUCT_ORANGE)
    assert body['selling_price'] == 45
    assert body['master_price'] == 1200
    assert body['product_name'] == 'Nagpur Orange'
    assert body['available_for_pos'] is True


def test_admin_can_set_franchise_selling_price(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'selling_price': 28},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['selling_price'] == 28
    assert body['master_price'] == 100


def test_admin_can_activate_deactivate_franchise_product(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['is_active'] is False
    assert body['available_for_pos'] is False

    response = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': True},
    )
    assert response.status_code == 200
    assert response.json()['is_active'] is True


def test_duplicate_assignment_rejected(client, auth_header_factory):
    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
        json={
            'product_id': str(PRODUCT_NIMBU),
            'selling_price': 30,
            'is_active': True,
        },
    )
    assert response.status_code == 409
    assert 'already assigned' in response.json()['detail'].lower()


def test_negative_price_rejected(client, auth_header_factory):
    product = client.post(
        '/api/v1/admin/products',
        headers=_admin(auth_header_factory),
        json={
            'name': 'Bad Price',
            'category_id': str(CATEGORY_ZEST),
            'price': -5,
        },
    )
    assert product.status_code == 422

    franchise = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
        headers=_admin(auth_header_factory),
        json={
            'product_id': str(PRODUCT_ORANGE),
            'selling_price': -1,
        },
    )
    assert franchise.status_code == 422


def test_non_admin_cannot_modify_products(client, auth_header_factory):
    for headers in (_owner(auth_header_factory), _employee(auth_header_factory)):
        create = client.post(
            '/api/v1/admin/products',
            headers=headers,
            json={
                'name': 'Unauthorized',
                'category_id': str(CATEGORY_ZEST),
                'price': 10,
            },
        )
        assert create.status_code == 403

        patch = client.patch(
            f'/api/v1/admin/products/{PRODUCT_NIMBU}',
            headers=headers,
            json={'price': 99},
        )
        assert patch.status_code == 403


def test_non_admin_cannot_modify_franchise_pricing(client, auth_header_factory):
    for headers in (_owner(auth_header_factory), _employee(auth_header_factory)):
        assign = client.post(
            f'/api/v1/admin/franchises/{FRANCHISE_B}/products',
            headers=headers,
            json={
                'product_id': str(PRODUCT_ORANGE),
                'selling_price': 50,
            },
        )
        assert assign.status_code == 403

        patch = client.patch(
            f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
            headers=headers,
            json={'selling_price': 99},
        )
        assert patch.status_code == 403


def test_franchise_product_list_returns_assignments(client, auth_header_factory):
    response = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
    )
    assert response.status_code == 200
    body = response.json()
    assert body['total'] >= 1
    item = next(i for i in body['items'] if i['product_id'] == str(PRODUCT_NIMBU))
    assert item['selling_price'] == 22
    assert item['master_price'] == 100
    assert item['product_name'] == 'Nimbu Pudina'
    assert item['category_name'] == 'Zest Collection'
    assert item['available_for_pos'] is True


def test_globally_inactive_product_not_available_for_pos(client, auth_header_factory):
    client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'is_active': False},
    )
    response = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products',
        headers=_admin(auth_header_factory),
    )
    item = next(i for i in response.json()['items'] if i['product_id'] == str(PRODUCT_NIMBU))
    assert item['product_is_active'] is False
    assert item['is_active'] is True
    assert item['available_for_pos'] is False


def _upload(client, headers, product_id, content: bytes, filename: str, content_type: str):
    return client.post(
        f'/api/v1/admin/products/{product_id}/image',
        headers=headers,
        files={'file': (filename, BytesIO(content), content_type)},
    )


def test_product_image_upload_jpeg(client, auth_header_factory, fake_db):
    response = _upload(
        client,
        _admin(auth_header_factory),
        PRODUCT_NIMBU,
        JPEG_BYTES,
        'nimbu.jpg',
        'image/jpeg',
    )
    assert response.status_code == 200
    body = response.json()
    assert body['metadata']['image_url']
    assert body['metadata']['image_path'].startswith(f'{PRODUCT_NIMBU}/')
    assert body['image_url'] == body['metadata']['image_url']
    assert any(k[0] == 'product-images' for k in fake_db.storage_objects)


def test_product_image_upload_png(client, auth_header_factory):
    response = _upload(
        client,
        _admin(auth_header_factory),
        PRODUCT_ORANGE,
        PNG_BYTES,
        'orange.png',
        'image/png',
    )
    assert response.status_code == 200
    assert response.json()['metadata']['image_path'].endswith('.png')


def test_product_image_upload_webp(client, auth_header_factory):
    response = _upload(
        client,
        _admin(auth_header_factory),
        PRODUCT_ORANGE,
        WEBP_BYTES,
        'orange.webp',
        'image/webp',
    )
    assert response.status_code == 200
    assert response.json()['metadata']['image_path'].endswith('.webp')


def test_unsupported_image_type_rejected(client, auth_header_factory):
    response = _upload(
        client,
        _admin(auth_header_factory),
        PRODUCT_NIMBU,
        GIF_BYTES,
        'bad.gif',
        'image/gif',
    )
    assert response.status_code == 400
    assert 'unsupported' in response.json()['detail'].lower()


def test_oversized_image_rejected(client, auth_header_factory):
    huge = b'\xff\xd8\xff\xe0' + (b'\x00' * (5 * 1024 * 1024 + 10))
    response = _upload(
        client,
        _admin(auth_header_factory),
        PRODUCT_NIMBU,
        huge,
        'huge.jpg',
        'image/jpeg',
    )
    assert response.status_code == 400
    assert 'maximum' in response.json()['detail'].lower() or 'size' in response.json()['detail'].lower()


def test_product_image_metadata_stored_correctly(client, auth_header_factory):
    response = _upload(
        client,
        _admin(auth_header_factory),
        PRODUCT_NIMBU,
        JPEG_BYTES,
        'meta.jpg',
        'image/jpeg',
    )
    meta = response.json()['metadata']
    assert 'image_url' in meta
    assert 'image_path' in meta
    assert 'emoji' not in meta
    assert '/product-images/' in meta['image_url']


def test_product_image_can_be_replaced(client, auth_header_factory, fake_db):
    first = _upload(
        client,
        _admin(auth_header_factory),
        PRODUCT_NIMBU,
        JPEG_BYTES,
        'first.jpg',
        'image/jpeg',
    )
    assert first.status_code == 200
    first_path = first.json()['metadata']['image_path']

    second = _upload(
        client,
        _admin(auth_header_factory),
        PRODUCT_NIMBU,
        PNG_BYTES,
        'second.png',
        'image/png',
    )
    assert second.status_code == 200
    second_path = second.json()['metadata']['image_path']
    assert second_path != first_path
    assert second_path.endswith('.png')
    assert ('product-images', first_path) not in fake_db.storage_objects
    assert ('product-images', second_path) in fake_db.storage_objects


def test_product_image_can_be_removed(client, auth_header_factory, fake_db):
    uploaded = _upload(
        client,
        _admin(auth_header_factory),
        PRODUCT_NIMBU,
        JPEG_BYTES,
        'remove.jpg',
        'image/jpeg',
    )
    path = uploaded.json()['metadata']['image_path']
    assert ('product-images', path) in fake_db.storage_objects

    response = client.delete(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}/image',
        headers=_admin(auth_header_factory),
    )
    assert response.status_code == 200
    body = response.json()
    assert body['image_url'] is None
    assert 'image_url' not in (body.get('metadata') or {})
    assert 'image_path' not in (body.get('metadata') or {})
    assert ('product-images', path) not in fake_db.storage_objects


def test_product_image_storage_failure_returns_503(client, auth_header_factory, fake_db):
    fake_db.fail_next_storage_upload = True
    response = _upload(
        client,
        _admin(auth_header_factory),
        PRODUCT_NIMBU,
        JPEG_BYTES,
        'fail.jpg',
        'image/jpeg',
    )
    assert response.status_code == 503
    assert 'unable to upload' in response.json()['detail'].lower()


def test_product_images_bucket_is_created_on_upload(client, auth_header_factory, fake_db):
    assert 'product-images' not in fake_db.storage.buckets
    response = _upload(
        client,
        _admin(auth_header_factory),
        PRODUCT_NIMBU,
        JPEG_BYTES,
        'bucket.jpg',
        'image/jpeg',
    )
    assert response.status_code == 200
    assert 'product-images' in fake_db.storage.buckets


def test_non_admin_cannot_upload_product_images(client, auth_header_factory):
    for headers in (_owner(auth_header_factory), _employee(auth_header_factory)):
        response = _upload(
            client,
            headers,
            PRODUCT_NIMBU,
            JPEG_BYTES,
            'nope.jpg',
            'image/jpeg',
        )
        assert response.status_code == 403

        delete = client.delete(
            f'/api/v1/admin/products/{PRODUCT_NIMBU}/image',
            headers=headers,
        )
        assert delete.status_code == 403
