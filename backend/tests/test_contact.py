import pytest

from app.modules.public.email import CONTACT_FAILURE_MESSAGE, EmailDeliveryError
from app.modules.public.rate_limit import reset_contact_rate_limiter
from app.modules.public.service import THANK_YOU_MESSAGE


@pytest.fixture(autouse=True)
def _reset_limiter():
    reset_contact_rate_limiter()
    yield
    reset_contact_rate_limiter()


VALID = {
    'name': 'Priya',
    'phone': '9876543210',
    'email': 'priya@example.com',
    'message': 'Do you offer kulfi catering?',
}


def test_valid_enquiry_is_accepted(client, fake_db, monkeypatch):
    sent: list[dict] = []

    def fake_send(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr('app.modules.public.service.send_contact_email', fake_send)
    response = client.post('/api/v1/public/contact', json=VALID)
    assert response.status_code == 200
    assert response.json()['message'] == THANK_YOU_MESSAGE
    assert sent[0]['email'] == 'priya@example.com'
    assert sent[0]['name'] == 'Priya'


def test_contact_does_not_create_franchise_application(client, fake_db, monkeypatch):
    before = list(fake_db.tables['franchise_applications'])
    monkeypatch.setattr('app.modules.public.service.send_contact_email', lambda **_: None)
    client.post('/api/v1/public/contact', json=VALID)
    assert fake_db.tables['franchise_applications'] == before


def test_invalid_email_is_rejected(client, monkeypatch):
    monkeypatch.setattr('app.modules.public.service.send_contact_email', lambda **_: None)
    response = client.post(
        '/api/v1/public/contact',
        json={**VALID, 'email': 'not-an-email'},
    )
    assert response.status_code == 422


def test_oversized_message_is_rejected(client, monkeypatch):
    monkeypatch.setattr('app.modules.public.service.send_contact_email', lambda **_: None)
    response = client.post(
        '/api/v1/public/contact',
        json={**VALID, 'message': 'x' * 2001},
    )
    assert response.status_code == 422


def test_honeypot_is_rejected(client, monkeypatch):
    called = {'n': 0}

    def fake_send(**kwargs):
        called['n'] += 1

    monkeypatch.setattr('app.modules.public.service.send_contact_email', fake_send)
    response = client.post(
        '/api/v1/public/contact',
        json={**VALID, 'website': 'https://spam.example'},
    )
    assert response.status_code == 400
    assert called['n'] == 0
    assert THANK_YOU_MESSAGE not in response.text


def test_resend_failure_returns_error(client, monkeypatch):
    def boom(**kwargs):
        raise EmailDeliveryError(CONTACT_FAILURE_MESSAGE)

    monkeypatch.setattr('app.modules.public.service.send_contact_email', boom)
    response = client.post('/api/v1/public/contact', json=VALID)
    assert response.status_code == 502
    assert response.json()['detail'] == CONTACT_FAILURE_MESSAGE
    assert THANK_YOU_MESSAGE not in response.text


def test_contact_secrets_are_never_returned(client, monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY', 're_secret_test_key_do_not_leak')
    monkeypatch.setenv('CONTACT_TO_EMAIL', 'team@example.com')
    monkeypatch.setenv('CONTACT_FROM_EMAIL', 'web@example.com')

    def boom(**kwargs):
        raise EmailDeliveryError(CONTACT_FAILURE_MESSAGE)

    monkeypatch.setattr('app.modules.public.service.send_contact_email', boom)
    response = client.post('/api/v1/public/contact', json=VALID)
    assert 're_secret_test_key_do_not_leak' not in response.text
    assert 'RESEND_API_KEY' not in response.text
    assert 'team@example.com' not in response.text
