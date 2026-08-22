from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.validation import (
    INVALID_PHONE,
    validate_amount,
    validate_email,
    validate_percentage,
    validate_phone,
    validate_price,
    validate_quantity,
    validate_required_text,
)
from app.modules.franchises.schemas import FranchiseCreate, FranchiseOfflinePaymentCreate, FranchiseOwnerCreate
from app.modules.products.schemas import FranchiseProductAssign, ProductCreate
from app.modules.public.schemas import ContactEnquiryRequest
from app.modules.users.schemas import AdminUserCreate


def test_phone_accepts_existing_storage_formats():
    assert validate_phone('+919876543210') == '+919876543210'
    assert validate_phone('919876543210') == '919876543210'
    assert validate_phone('9876543210') == '9876543210'
    assert validate_phone('+91 98765 43210') == '+919876543210'
    assert validate_phone(None) is None
    assert validate_phone('') is None
    assert validate_phone('   ') is None


def test_phone_rejects_invalid_values():
    for value in ('+91abc1234567', '+91987654321', '+9198765432100', '1234567890', 'phone', '+91-abc'):
        with pytest.raises(ValueError, match='valid Indian phone'):
            validate_phone(value)


def test_email_valid_and_invalid():
    assert validate_email('Owner@RealStick.in', required=True) == 'owner@realstick.in'
    with pytest.raises(ValueError, match='Invalid email format'):
        validate_email('not-an-email', required=True)
    with pytest.raises(ValueError, match='Email is required'):
        validate_email('   ', required=True)


def test_price_and_selling_price_rules():
    assert validate_price('100', allow_zero=True) == Decimal('100')
    assert validate_price('100.50', allow_zero=True) == Decimal('100.50')
    assert validate_price(0, allow_zero=True) == Decimal('0')
    with pytest.raises(ValueError, match='2 decimal'):
        validate_price('100.123', allow_zero=True)
    with pytest.raises(ValueError, match='cannot be negative'):
        validate_price(-100, allow_zero=True)
    with pytest.raises(ValueError, match='greater than 0'):
        validate_price(0, allow_zero=False)


def test_amount_quantity_and_percentage():
    assert validate_amount('250.50') == Decimal('250.50')
    with pytest.raises(ValueError, match='greater than 0'):
        validate_amount(0)
    with pytest.raises(ValueError, match='2 decimal'):
        validate_amount('10.999')
    assert validate_quantity(3) == 3
    with pytest.raises(ValueError, match='valid whole number'):
        validate_quantity('abc')
    assert validate_percentage('12.5') == Decimal('12.5')
    with pytest.raises(ValueError, match='at most 100'):
        validate_percentage(150)


def test_required_text_trims_and_rejects_blank():
    assert validate_required_text('  Hyderabad  ', field_name='Outlet name') == 'Hyderabad'
    with pytest.raises(ValueError, match='Outlet name is required'):
        validate_required_text('   ', field_name='Outlet name')


def test_schema_phone_and_email_validation():
    owner = FranchiseOwnerCreate(full_name='Asha', email='asha@realstick.in', phone='9876543210')
    assert owner.phone == '9876543210'
    with pytest.raises(ValidationError):
        FranchiseOwnerCreate(full_name='Asha', email='asha@realstick.in', phone='+91abc1234567')
    with pytest.raises(ValidationError):
        AdminUserCreate(full_name='Admin', email='bad-email', role='SYSTEM_ADMIN')


def test_schema_price_and_amount_validation():
    product = ProductCreate(
        name='Nimbu',
        category_id='11111111-1111-1111-1111-111111111111',
        price='100.50',
    )
    assert product.price == Decimal('100.50')
    with pytest.raises(ValidationError):
        ProductCreate(
            name='Nimbu',
            category_id='11111111-1111-1111-1111-111111111111',
            price='100.123',
        )
    assignment = FranchiseProductAssign(
        product_id='11111111-1111-1111-1111-111111111111',
        selling_price='80',
    )
    assert assignment.selling_price == Decimal('80')
    with pytest.raises(ValidationError):
        FranchiseProductAssign(
            product_id='11111111-1111-1111-1111-111111111111',
            selling_price=0,
        )
    payment = FranchiseOfflinePaymentCreate(
        amount='1500.25',
        paid_at='2026-08-22',
        payment_method='CASH',
    )
    assert payment.amount == Decimal('1500.25')
    with pytest.raises(ValidationError):
        FranchiseOfflinePaymentCreate(
            amount='1500.255',
            paid_at='2026-08-22',
            payment_method='CASH',
        )


def test_contact_phone_and_franchise_create_use_shared_phone_rule():
    contact = ContactEnquiryRequest(
        name='Priya',
        phone='+919876543210',
        email='priya@example.com',
        message='Hello',
    )
    assert contact.phone == '+919876543210'
    created = FranchiseCreate(name='New Outlet', owner_phone='9876543210')
    assert created.owner_phone == '9876543210'
    with pytest.raises(ValidationError):
        FranchiseCreate(name='New Outlet', owner_phone='+91987654321')
