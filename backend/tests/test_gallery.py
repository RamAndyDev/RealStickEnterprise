from io import BytesIO
from uuid import uuid4

from tests.conftest import ADMIN_ID, EMPLOYEE_ID, OWNER_ID

PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
    b'\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
)

PUBLIC_FORBIDDEN_KEYS = {
    'uploaded_by',
    'storage_path',
    'franchise_id',
    'is_approved',
    'is_archived',
    'created_at',
    'updated_at',
}


def _item(fake_db, **overrides):
    now = fake_db.tables['products'][0]['created_at']
    row = {
        'id': str(uuid4()),
        'franchise_id': None,
        'title': 'Gallery item',
        'caption': 'A caption',
        'author_name': None,
        'media_type': 'IMAGE',
        'storage_path': 'path.jpg',
        'media_url': 'https://example.supabase.co/storage/v1/object/public/gallery/path.jpg',
        'display_order': 1,
        'is_approved': True,
        'is_archived': False,
        'uploaded_by': str(ADMIN_ID),
        'created_at': now,
        'updated_at': now,
    }
    row.update(overrides)
    fake_db.tables['gallery_items'].append(row)
    return row


def test_public_gallery_requires_no_auth_and_whitelists_fields(client, fake_db):
    approved = _item(fake_db, title='Approved image', display_order=2)
    _item(fake_db, title='Hidden draft', is_approved=False)
    _item(fake_db, title='Hidden archive', is_archived=True)
    response = client.get('/api/v1/public/gallery')
    assert response.status_code == 200
    items = response.json()['items']
    titles = {item['title'] for item in items}
    assert approved['title'] in titles
    assert 'Hidden draft' not in titles
    assert 'Hidden archive' not in titles
    for item in items:
        assert PUBLIC_FORBIDDEN_KEYS.isdisjoint(item.keys())
        assert set(item.keys()) <= {
            'id',
            'title',
            'caption',
            'author_name',
            'media_type',
            'media_url',
            'display_order',
        }


def test_public_gallery_sorts_by_display_order(client, fake_db):
    _item(fake_db, title='Second', display_order=2)
    _item(fake_db, title='First', display_order=1)
    titles = [item['title'] for item in client.get('/api/v1/public/gallery').json()['items']]
    assert titles[:2] == ['First', 'Second']


def test_admin_gallery_create_update_archive_approve(client, fake_db, auth_header_factory):
    headers = auth_header_factory(ADMIN_ID, 'admin@realstick.in')
    created = client.post(
        '/api/v1/admin/gallery',
        headers=headers,
        json={
            'media_type': 'TESTIMONIAL',
            'title': 'A guest',
            'caption': 'Real fruits. Real goodness.',
            'author_name': 'A. Guest',
            'display_order': 3,
        },
    )
    assert created.status_code == 201
    item_id = created.json()['id']
    assert created.json()['is_approved'] is False
    assert created.json()['media_type'] == 'TESTIMONIAL'

    updated = client.patch(
        f'/api/v1/admin/gallery/{item_id}',
        headers=headers,
        json={'is_approved': True, 'caption': 'Updated quote'},
    )
    assert updated.status_code == 200
    assert updated.json()['is_approved'] is True
    assert updated.json()['caption'] == 'Updated quote'

    archived = client.patch(
        f'/api/v1/admin/gallery/{item_id}',
        headers=headers,
        json={'is_archived': True},
    )
    assert archived.status_code == 200
    assert archived.json()['is_archived'] is True

    public_titles = {item['title'] for item in client.get('/api/v1/public/gallery').json()['items']}
    assert 'A guest' not in public_titles

    unapproved = client.patch(
        f'/api/v1/admin/gallery/{item_id}',
        headers=headers,
        json={'is_archived': False, 'is_approved': False},
    )
    assert unapproved.json()['is_approved'] is False
    public_titles = {item['title'] for item in client.get('/api/v1/public/gallery').json()['items']}
    assert 'A guest' not in public_titles


def test_admin_can_create_video_and_upload_image(client, fake_db, auth_header_factory):
    headers = auth_header_factory(ADMIN_ID, 'admin@realstick.in')
    video = client.post(
        '/api/v1/admin/gallery',
        headers=headers,
        json={
            'media_type': 'VIDEO',
            'title': 'Kitchen',
            'media_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'is_approved': True,
        },
    )
    assert video.status_code == 201
    assert video.json()['media_url'].startswith('https://')

    image = client.post(
        '/api/v1/admin/gallery',
        headers=headers,
        json={'media_type': 'IMAGE', 'title': 'Popsicle'},
    )
    assert image.status_code == 201
    item_id = image.json()['id']
    upload = client.post(
        f'/api/v1/admin/gallery/{item_id}/media',
        headers=headers,
        files={'file': ('stick.png', BytesIO(PNG_BYTES), 'image/png')},
    )
    assert upload.status_code == 200
    assert '/gallery/' in upload.json()['media_url']
    assert any(key[0] == 'gallery' for key in fake_db.storage_objects)


def test_owner_and_employee_cannot_manage_gallery(client, auth_header_factory):
    owner = auth_header_factory(OWNER_ID, 'owner@realstick.in')
    employee = auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in')
    for headers in (owner, employee):
        listed = client.get('/api/v1/admin/gallery', headers=headers)
        assert listed.status_code == 403
        created = client.post(
            '/api/v1/admin/gallery',
            headers=headers,
            json={
                'media_type': 'TESTIMONIAL',
                'caption': 'Nope',
                'author_name': 'X',
            },
        )
        assert created.status_code == 403
