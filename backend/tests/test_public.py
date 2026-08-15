from uuid import uuid4

from tests.conftest import CATEGORY_ZEST, PRODUCT_NIMBU, PRODUCT_ORANGE


INTERNAL_PRODUCT_KEYS = {
    'price',
    'min_price',
    'max_price',
    'sku',
    'metadata',
    'franchise_id',
    'selling_price',
    'is_active',
    'created_at',
    'updated_at',
    'available_for_pos',
    'price_editable',
}


def test_public_categories_require_no_auth(client, fake_db):
    response = client.get('/api/v1/public/categories')
    assert response.status_code == 200
    names = {item['name'] for item in response.json()['items']}
    assert 'Zest Collection' in names
    assert 'Garden Collection' in names


def test_public_categories_hide_inactive(client, fake_db):
    fake_db.tables['product_categories'][0]['is_active'] = False
    response = client.get('/api/v1/public/categories')
    names = {item['name'] for item in response.json()['items']}
    assert 'Zest Collection' not in names
    assert 'Garden Collection' in names


def test_public_products_require_no_auth_and_hide_prices(client):
    response = client.get('/api/v1/public/products')
    assert response.status_code == 200
    payload = response.json()
    names = {item['name'] for item in payload['items']}
    assert 'Nimbu Pudina' in names
    assert 'Nagpur Orange' in names
    for item in payload['items']:
        assert INTERNAL_PRODUCT_KEYS.isdisjoint(item.keys())
        assert 'price' not in item
        assert 'selling_price' not in item
        assert 'sku' not in item
        assert 'metadata' not in item
        assert 'franchise_id' not in item
        assert set(item.keys()) <= {
            'id',
            'category_id',
            'category_name',
            'name',
            'description',
            'image_url',
        }


def test_public_products_hide_inactive_product(client, fake_db):
    for row in fake_db.tables['products']:
        if row['id'] == str(PRODUCT_NIMBU):
            row['is_active'] = False
    names = {item['name'] for item in client.get('/api/v1/public/products').json()['items']}
    assert 'Nimbu Pudina' not in names
    assert 'Nagpur Orange' in names


def test_public_products_hide_inactive_category(client, fake_db):
    for row in fake_db.tables['product_categories']:
        if row['id'] == str(CATEGORY_ZEST):
            row['is_active'] = False
    names = {item['name'] for item in client.get('/api/v1/public/products').json()['items']}
    assert 'Nimbu Pudina' not in names
    assert 'Nagpur Orange' in names


def test_public_products_hide_uncategorized(client, fake_db):
    for row in fake_db.tables['products']:
        if row['id'] == str(PRODUCT_ORANGE):
            row['category_id'] = None
    names = {item['name'] for item in client.get('/api/v1/public/products').json()['items']}
    assert 'Nagpur Orange' not in names
    assert 'Nimbu Pudina' in names


def test_public_products_do_not_require_franchise_assignment(client, fake_db):
    fake_db.tables['franchise_product_prices'].clear()
    names = {item['name'] for item in client.get('/api/v1/public/products').json()['items']}
    assert 'Nimbu Pudina' in names
    assert 'Nagpur Orange' in names


def test_public_products_never_return_franchise_information(client, fake_db):
    extra = {
        'id': str(uuid4()),
        'category_id': str(CATEGORY_ZEST),
        'sku': 'SECRET-SKU',
        'name': 'Secret Stick',
        'description': 'Should appear without internals',
        'image_url': None,
        'price': 999,
        'min_price': 1,
        'max_price': 2,
        'is_active': True,
        'metadata': {'image_path': 'hidden'},
        'created_at': fake_db.tables['products'][0]['created_at'],
        'updated_at': fake_db.tables['products'][0]['updated_at'],
    }
    fake_db.tables['products'].append(extra)
    item = next(
        row
        for row in client.get('/api/v1/public/products').json()['items']
        if row['name'] == 'Secret Stick'
    )
    assert 'sku' not in item
    assert 'metadata' not in item
    assert 'price' not in item
    assert item['description'] == 'Should appear without internals'
