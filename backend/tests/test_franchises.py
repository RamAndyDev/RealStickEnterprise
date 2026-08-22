from uuid import uuid4

from app.modules.franchises.schemas import OWNER_EMAIL_EXISTS_DETAIL
from tests.conftest import (
    ADMIN_ID,
    EMPLOYEE_ID,
    FRANCHISE_A,
    FRANCHISE_B,
    OWNER_CANDIDATE_ID,
    OWNER_ID,
)


def test_admin_can_list_franchises(client, auth_header_factory):
    response = client.get(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
    )
    assert response.status_code == 200
    body = response.json()
    assert body['total'] >= 2
    names = {item['name'] for item in body['items']}
    assert 'Hyderabad — Main Store' in names


def test_admin_can_create_franchise(client, auth_header_factory):
    response = client.post(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={
            'name': 'Gachibowli Outlet',
            'city': 'Hyderabad',
            'state': 'Telangana',
            'address': 'Financial District',
            'owner_email': 'gachi.owner@realstick.in',
            'tier': 'Founder',
            'open_date': '2026-09-01',
            'code': 'GACHI-01',
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body['name'] == 'Gachibowli Outlet'
    assert body['tier'] == 'Founder'
    assert body['status'] == 'SETUP'
    assert body['launch_progress_total'] >= 1
    assert len(body['launch_checklist']) >= 1


def test_admin_can_create_franchise_with_new_owner(client, auth_header_factory, fake_db):
    before_ids = {row['id'] for row in fake_db.tables['franchises']}
    response = client.post(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={
            'name': 'Kondapur Outlet',
            'city': 'Hyderabad',
            'owner_full_name': 'Kondapur Owner',
            'owner_email': 'kondapur.owner@realstick.in',
            'owner_phone': '9876543210',
            'tier': 'Founder',
            'code': 'KOND-01',
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body['name'] == 'Kondapur Outlet'
    assert body['owner_email'] == 'kondapur.owner@realstick.in'
    assert body['owner'] is not None
    assert body['owner']['full_name'] == 'Kondapur Owner'
    assert body['owner']['is_active'] is True

    created_ids = {row['id'] for row in fake_db.tables['franchises']} - before_ids
    assert created_ids == {body['id']}
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == body['owner']['id'])
    assert profile['role'] == 'FRANCHISE_OWNER'
    assert profile['franchise_id'] == body['id']
    assert any(u.email == 'kondapur.owner@realstick.in' for u in fake_db.auth.admin._users)


def test_duplicate_owner_email_does_not_create_franchise(client, auth_header_factory, fake_db):
    before_franchises = list(fake_db.tables['franchises'])
    before_profiles = list(fake_db.tables['profiles'])
    response = client.post(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={
            'name': 'Orphan Risk Outlet',
            'owner_full_name': 'Existing Email Owner',
            'owner_email': 'owner@realstick.in',
            'code': 'ORPHAN-01',
        },
    )
    assert response.status_code == 409
    assert response.json()['detail'] == OWNER_EMAIL_EXISTS_DETAIL
    assert 'assign' not in response.json()['detail'].lower()
    assert fake_db.tables['franchises'] == before_franchises
    assert not any(row.get('name') == 'Orphan Risk Outlet' for row in fake_db.tables['franchises'])
    assert not any(row.get('code') == 'ORPHAN-01' for row in fake_db.tables['franchises'])
    assert fake_db.tables['profiles'] == before_profiles


def test_owner_create_failure_rolls_back_new_franchise(client, auth_header_factory, fake_db, monkeypatch):
    from fastapi import HTTPException

    from app.modules.franchises.service import FranchiseService

    def fail_owner(self, franchise_id, data, actor):
        raise HTTPException(status_code=400, detail='Unable to create franchise owner profile')

    monkeypatch.setattr(FranchiseService, 'create_owner', fail_owner)
    before_franchises = list(fake_db.tables['franchises'])
    response = client.post(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={
            'name': 'Rollback Outlet',
            'owner_full_name': 'Rollback Owner',
            'owner_email': 'rollback.owner@realstick.in',
            'code': 'ROLLBACK-01',
        },
    )
    assert response.status_code == 400
    assert not any(row.get('name') == 'Rollback Outlet' for row in fake_db.tables['franchises'])
    assert not any(row.get('code') == 'ROLLBACK-01' for row in fake_db.tables['franchises'])
    assert fake_db.tables['franchises'] == before_franchises


def test_failed_owner_create_then_retry_creates_exactly_one_outlet(client, auth_header_factory, fake_db):
    before_ids = {row['id'] for row in fake_db.tables['franchises']}
    failed = client.post(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={
            'name': 'Retry Outlet',
            'owner_full_name': 'Retry Owner',
            'owner_email': 'owner@realstick.in',
            'code': 'RETRY-01',
        },
    )
    assert failed.status_code == 409
    assert {row['id'] for row in fake_db.tables['franchises']} == before_ids

    retry = client.post(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={
            'name': 'Retry Outlet',
            'owner_full_name': 'Retry Owner',
            'owner_email': 'retry.owner@realstick.in',
            'code': 'RETRY-01',
        },
    )
    assert retry.status_code == 201
    body = retry.json()
    created_ids = {row['id'] for row in fake_db.tables['franchises']} - before_ids
    assert created_ids == {body['id']}
    assert body['owner']['full_name'] == 'Retry Owner'
    assert body['owner_email'] == 'retry.owner@realstick.in'
    owners = [
        p
        for p in fake_db.tables['profiles']
        if p.get('franchise_id') == body['id'] and p.get('role') == 'FRANCHISE_OWNER' and p.get('is_active')
    ]
    assert len(owners) == 1


def test_admin_can_create_franchise_owner(client, auth_header_factory, fake_db):
    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owners',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={
            'full_name': 'New Outlet Owner',
            'email': 'new.owner@realstick.in',
            'phone': '9876543210',
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert 'password' not in body
    assert body['password_setup'] in {'invite_email_sent', 'recovery_email_sent'}
    assert body['owner']['full_name'] == 'New Outlet Owner'
    assert body['owner']['is_active'] is True
    assert body['franchise']['owner']['id'] == body['owner']['id']
    assert body['franchise']['owner_email'] == 'new.owner@realstick.in'

    owner_id = body['owner']['id']
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == owner_id)
    assert profile['role'] == 'FRANCHISE_OWNER'
    assert profile['franchise_id'] == str(FRANCHISE_B)
    assert profile['full_name'] == 'New Outlet Owner'
    assert 'password' not in profile

    auth_emails = [u.email for u in fake_db.auth.admin._users]
    assert 'new.owner@realstick.in' in auth_emails
    assert any(item['email'] == 'new.owner@realstick.in' for item in fake_db.auth.admin.invites)


def test_owner_invite_fallback_sends_recovery_email(client, auth_header_factory, fake_db):
    fake_db.auth.admin.fail_next_invite = True
    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owners',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={
            'full_name': 'Fallback Owner',
            'email': 'fallback.owner@realstick.in',
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body['password_setup'] == 'recovery_email_sent'
    assert body['owner']['full_name'] == 'Fallback Owner'
    assert any(item['email'] == 'fallback.owner@realstick.in' for item in fake_db.auth.recovery_emails)


def test_created_owner_auth_and_profile_are_linked(client, auth_header_factory, fake_db):
    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owners',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'full_name': 'Linked Owner', 'email': 'linked.owner@realstick.in'},
    )
    assert response.status_code == 201
    owner_id = response.json()['owner']['id']
    assert any(str(u.id) == owner_id for u in fake_db.auth.admin._users)
    profile = next(p for p in fake_db.tables['profiles'] if p['id'] == owner_id)
    assert profile['role'] == 'FRANCHISE_OWNER'
    assert profile['franchise_id'] == str(FRANCHISE_B)


def test_non_admin_cannot_create_franchise_owner(client, auth_header_factory):
    owner = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owners',
        headers=auth_header_factory(OWNER_ID, 'owner@realstick.in'),
        json={'full_name': 'Nope', 'email': 'nope@realstick.in'},
    )
    employee = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owners',
        headers=auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in'),
        json={'full_name': 'Nope', 'email': 'nope2@realstick.in'},
    )
    assert owner.status_code == 403
    assert employee.status_code == 403


def test_duplicate_or_invalid_owner_create_handled(client, auth_header_factory):
    invalid_email = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owners',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'full_name': 'Bad Email', 'email': 'not-an-email'},
    )
    assert invalid_email.status_code == 422

    missing_name = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owners',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'full_name': '  ', 'email': 'blank.name@realstick.in'},
    )
    assert missing_name.status_code == 422

    duplicate = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owners',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'full_name': 'Existing', 'email': 'owner@realstick.in'},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()['detail'] == 'Email already exists. Please use a different email address.'
    assert 'assign' not in duplicate.json()['detail'].lower()


def test_create_owner_reassignment_deactivates_previous(client, auth_header_factory, fake_db):
    # FRANCHISE_A already has OWNER_ID as active owner.
    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/owners',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'full_name': 'Replacement Owner', 'email': 'replacement@realstick.in'},
    )
    assert response.status_code == 201
    new_owner_id = response.json()['owner']['id']

    previous = next(p for p in fake_db.tables['profiles'] if p['id'] == str(OWNER_ID))
    assert previous['is_active'] is False

    active_owners = [
        p
        for p in fake_db.tables['profiles']
        if p.get('franchise_id') == str(FRANCHISE_A)
        and p.get('role') == 'FRANCHISE_OWNER'
        and p.get('is_active')
    ]
    assert len(active_owners) == 1
    assert active_owners[0]['id'] == new_owner_id


def test_admin_can_assign_owner(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owner',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={
            'owner_profile_id': str(OWNER_CANDIDATE_ID),
            'owner_email': 'candidate@realstick.in',
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body['owner'] is not None
    assert body['owner']['id'] == str(OWNER_CANDIDATE_ID)
    assert body['owner_email'] == 'candidate@realstick.in'


def test_reassignment_via_assign_respects_active_owner_constraint(client, auth_header_factory, fake_db):
    # Promote candidate onto FRANCHISE_B (no prior owner).
    first = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owner',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'owner_profile_id': str(OWNER_CANDIDATE_ID)},
    )
    assert first.status_code == 200

    # Create a second employee-like profile under FRANCHISE_B to reassign to.
    from uuid import uuid4

    second_id = str(uuid4())
    fake_db.tables['profiles'].append(
        {
            'id': second_id,
            'full_name': 'Second Candidate',
            'role': 'EMPLOYEE',
            'franchise_id': str(FRANCHISE_B),
            'phone': None,
            'is_active': True,
        }
    )
    fake_db.auth.admin._users.append(
        type('U', (), {'id': second_id, 'email': 'second@realstick.in'})()
    )

    second = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owner',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'owner_profile_id': second_id, 'owner_email': 'second@realstick.in'},
    )
    assert second.status_code == 200

    active_owners = [
        p
        for p in fake_db.tables['profiles']
        if p.get('franchise_id') == str(FRANCHISE_B)
        and p.get('role') == 'FRANCHISE_OWNER'
        and p.get('is_active')
    ]
    assert len(active_owners) == 1
    assert active_owners[0]['id'] == second_id

    previous = next(p for p in fake_db.tables['profiles'] if p['id'] == str(OWNER_CANDIDATE_ID))
    assert previous['is_active'] is False


def test_admin_can_update_franchise(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_B}',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={
            'name': 'Secunderabad Express',
            'city': 'Secunderabad',
            'tier': 'Scale',
            'address': 'Updated Address',
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body['name'] == 'Secunderabad Express'
    assert body['tier'] == 'Scale'
    assert body['address'] == 'Updated Address'


def test_admin_can_change_franchise_status(client, auth_header_factory):
    response = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/status',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'status': 'SUSPENDED'},
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'SUSPENDED'

    closed = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/status',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'status': 'CLOSED'},
    )
    assert closed.status_code == 200
    assert closed.json()['status'] == 'CLOSED'
    assert closed.json()['closed_at'] is not None


def test_non_admin_receives_403_on_franchise_list(client, auth_header_factory):
    owner = client.get(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(OWNER_ID, 'owner@realstick.in'),
    )
    employee = client.get(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in'),
    )
    assert owner.status_code == 403
    assert employee.status_code == 403


def test_invalid_franchise_data_rejected(client, auth_header_factory):
    bad_tier = client.post(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'name': 'Bad Tier Outlet', 'tier': 'Platinum'},
    )
    assert bad_tier.status_code == 422

    bad_email = client.post(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'name': 'Bad Email Outlet', 'owner_email': 'not-an-email'},
    )
    assert bad_email.status_code == 422

    bad_status = client.post(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'name': 'Bad Status Outlet', 'status': 'active'},
    )
    assert bad_status.status_code == 422

    missing_name = client.post(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'city': 'Hyderabad'},
    )
    assert missing_name.status_code == 422

    duplicate_code = client.post(
        '/api/v1/admin/franchises',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'name': 'Dup Code', 'code': 'HYD-MAIN'},
    )
    assert duplicate_code.status_code == 409


def test_duplicate_or_invalid_owner_assignment_rejected(client, auth_header_factory):
    # Already active owner of FRANCHISE_A cannot be assigned to FRANCHISE_B
    conflict = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owner',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'owner_profile_id': str(OWNER_ID)},
    )
    assert conflict.status_code == 409

    # SYSTEM_ADMIN cannot be owner
    admin_as_owner = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owner',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'owner_profile_id': str(ADMIN_ID)},
    )
    assert admin_as_owner.status_code == 400

    # Unknown profile
    missing = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owner',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'owner_profile_id': str(uuid4())},
    )
    assert missing.status_code == 404

    # Unknown email
    missing_email = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/owner',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'owner_email': 'nobody@realstick.in'},
    )
    assert missing_email.status_code == 404


def test_franchise_retrieval_works(client, auth_header_factory):
    response = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_A}',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
    )
    assert response.status_code == 200
    body = response.json()
    assert body['id'] == str(FRANCHISE_A)
    assert body['name'] == 'Hyderabad — Main Store'
    assert body['payment_status'] == 'COMPLETED'
    assert body['owner'] is not None
    assert len(body['payments']) >= 1


def test_application_retrieval_works(client, auth_header_factory):
    listed = client.get(
        '/api/v1/admin/franchise-applications',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
    )
    assert listed.status_code == 200
    assert listed.json()['total'] >= 1
    application_id = listed.json()['items'][0]['id']

    detail = client.get(
        f'/api/v1/admin/franchise-applications/{application_id}',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
    )
    assert detail.status_code == 200
    assert detail.json()['applicant_name'] == 'Asha Reddy'

    # Also available on franchise detail
    franchise = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_A}',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
    )
    assert franchise.status_code == 200
    assert len(franchise.json()['applications']) >= 1


def test_launch_checklist_progress_retrieval_works(client, auth_header_factory):
    response = client.get(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/launch-checklist',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 2
    completed = [i for i in items if i['is_completed']]
    assert len(completed) >= 1

    pending = next(i for i in items if not i['is_completed'])
    updated = client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/launch-checklist/{pending["id"]}',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json={'is_completed': True},
    )
    assert updated.status_code == 200
    assert updated.json()['is_completed'] is True


def _offline_payment_payload(**overrides):
    body = {
        'amount': 250000.50,
        'paid_at': '2026-08-20',
        'payment_method': 'BANK_TRANSFER',
        'reference_number': 'NEFT-8891',
        'notes': 'Received at head office',
    }
    body.update(overrides)
    return body


def test_admin_can_record_offline_franchise_payment(client, auth_header_factory, fake_db):
    before = [
        row
        for row in fake_db.tables['franchise_payments']
        if row['franchise_id'] == str(FRANCHISE_B)
    ]
    assert before == []

    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/payments',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json=_offline_payment_payload(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body['payment_status'] == 'COMPLETED'
    assert len(body['payments']) == 1
    payment = body['payments'][0]
    assert payment['status'] == 'COMPLETED'
    assert payment['amount'] == 250000.50
    assert payment['payment_method'] == 'BANK_TRANSFER'
    assert payment['reference_number'] == 'NEFT-8891'
    assert payment['notes'] == 'Received at head office'
    assert payment['paid_at'].startswith('2026-08-20')

    stored = [
        row
        for row in fake_db.tables['franchise_payments']
        if row['franchise_id'] == str(FRANCHISE_B)
    ]
    assert len(stored) == 1
    assert stored[0]['status'] == 'COMPLETED'


def test_non_admin_cannot_record_offline_franchise_payment(client, auth_header_factory):
    owner = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/payments',
        headers=auth_header_factory(OWNER_ID, 'owner@realstick.in'),
        json=_offline_payment_payload(),
    )
    employee = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/payments',
        headers=auth_header_factory(EMPLOYEE_ID, 'employee@realstick.in'),
        json=_offline_payment_payload(),
    )
    assert owner.status_code == 403
    assert employee.status_code == 403


def test_offline_payment_rejects_non_positive_amount(client, auth_header_factory):
    zero = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/payments',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json=_offline_payment_payload(amount=0),
    )
    negative = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/payments',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json=_offline_payment_payload(amount=-10),
    )
    extra_decimals = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/payments',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json=_offline_payment_payload(amount='12.345'),
    )
    assert zero.status_code == 422
    assert negative.status_code == 422
    assert extra_decimals.status_code == 422


def test_offline_payment_rejects_invalid_payment_method(client, auth_header_factory):
    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/payments',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json=_offline_payment_payload(payment_method='CARD'),
    )
    assert response.status_code == 422

    missing = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/payments',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json=_offline_payment_payload(payment_method='NOT_A_METHOD'),
    )
    assert missing.status_code == 422

    bad_date = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_B}/payments',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json=_offline_payment_payload(paid_at='21-08-2026'),
    )
    assert bad_date.status_code == 422


def test_offline_payment_preserves_existing_payment_history(client, auth_header_factory, fake_db):
    existing = [
        row
        for row in fake_db.tables['franchise_payments']
        if row['franchise_id'] == str(FRANCHISE_A)
    ]
    assert len(existing) == 1
    original_id = existing[0]['id']
    original_reference = existing[0]['reference_number']

    response = client.post(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/payments',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json=_offline_payment_payload(
            amount=1000,
            payment_method='CASH',
            reference_number='CASH-002',
            notes=None,
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body['payment_status'] == 'COMPLETED'
    assert len(body['payments']) == 2
    references = {item['reference_number'] for item in body['payments']}
    assert original_reference in references
    assert 'CASH-002' in references

    stored = [
        row
        for row in fake_db.tables['franchise_payments']
        if row['franchise_id'] == str(FRANCHISE_A)
    ]
    assert len(stored) == 2
    assert any(row['id'] == original_id and row['reference_number'] == original_reference for row in stored)


def test_offline_payment_unknown_franchise_is_not_found(client, auth_header_factory):
    response = client.post(
        f'/api/v1/admin/franchises/{uuid4()}/payments',
        headers=auth_header_factory(ADMIN_ID, 'admin@realstick.in'),
        json=_offline_payment_payload(),
    )
    assert response.status_code == 404
