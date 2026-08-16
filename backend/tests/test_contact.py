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
    assert sent[0]['enquiry_type'] == 'General Enquiry'


def test_complaint_enquiry_is_accepted(client, monkeypatch):
    sent: list[dict] = []
    monkeypatch.setattr('app.modules.public.service.send_contact_email', lambda **kwargs: sent.append(kwargs))
    response = client.post(
        '/api/v1/public/contact',
        json={**VALID, 'enquiry_type': 'COMPLAINT', 'message': 'The last order was melted.'},
    )
    assert response.status_code == 200
    assert response.json()['message'] == THANK_YOU_MESSAGE
    assert sent[0]['enquiry_type'] == 'Complaint'


def test_invalid_enquiry_type_is_rejected(client, monkeypatch):
    monkeypatch.setattr('app.modules.public.service.send_contact_email', lambda **_: None)
    response = client.post('/api/v1/public/contact', json={**VALID, 'enquiry_type': 'COUPON'})
    assert response.status_code == 422


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


def test_missing_resend_configuration_does_not_show_success(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv('RESEND_API_KEY', '')
    monkeypatch.setenv('CONTACT_TO_EMAIL', '')
    monkeypatch.setenv('CONTACT_FROM_EMAIL', '')
    get_settings.cache_clear()
    response = client.post('/api/v1/public/contact', json=VALID)
    assert response.status_code == 502
    assert response.json()['detail'] == CONTACT_FAILURE_MESSAGE
    assert THANK_YOU_MESSAGE not in response.text


def test_invalid_resend_api_key_does_not_show_success(client, monkeypatch):
    from types import SimpleNamespace

    from app.core.config import get_settings

    monkeypatch.setenv('RESEND_API_KEY', 're_invalid')
    monkeypatch.setenv('CONTACT_TO_EMAIL', 'team@example.com')
    monkeypatch.setenv('CONTACT_FROM_EMAIL', 'web@example.com')
    get_settings.cache_clear()
    monkeypatch.setattr(
        'app.modules.public.email.httpx.post',
        lambda *args, **kwargs: SimpleNamespace(status_code=401, text='unauthorized'),
    )
    response = client.post('/api/v1/public/contact', json=VALID)
    assert response.status_code == 502
    assert response.json()['detail'] == CONTACT_FAILURE_MESSAGE
    assert THANK_YOU_MESSAGE not in response.text
    assert 're_invalid' not in response.text


def test_contact_rate_limit_is_enforced(client, monkeypatch):
    monkeypatch.setattr('app.modules.public.service.send_contact_email', lambda **_: None)
    for _ in range(5):
        assert client.post('/api/v1/public/contact', json=VALID).status_code == 200
    limited = client.post('/api/v1/public/contact', json=VALID)
    assert limited.status_code == 429
    assert THANK_YOU_MESSAGE not in limited.text


def test_contact_options_are_empty_when_unconfigured(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv('PUBLIC_CONTACT_PHONE', '')
    monkeypatch.setenv('PUBLIC_CONTACT_WHATSAPP', '')
    monkeypatch.setenv('PUBLIC_CONTACT_EMAIL', '')
    get_settings.cache_clear()
    response = client.get('/api/v1/public/contact-options')
    assert response.status_code == 200
    body = response.json()
    assert body['phone'] is None
    assert body['whatsapp_url'] is None
    assert body['mailto_url'] is None


def test_contact_options_use_configured_whatsapp(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv('PUBLIC_CONTACT_WHATSAPP', '+91 99999 88888')
    monkeypatch.setenv('PUBLIC_CONTACT_PHONE', '0401234567')
    monkeypatch.setenv('PUBLIC_CONTACT_EMAIL', 'hello@realstick.in')
    get_settings.cache_clear()
    response = client.get('/api/v1/public/contact-options')
    assert response.status_code == 200
    body = response.json()
    assert body['whatsapp_url'] == 'https://wa.me/919999988888'
    assert body['tel_url'] == 'tel:0401234567'
    assert body['mailto_url'] == 'mailto:hello@realstick.in'
