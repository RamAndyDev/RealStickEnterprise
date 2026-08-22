import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { sellingPriceError } from '../src/types/product.ts';
import { paidAmountError } from '../src/features/franchises/offlinePayment.ts';
import { OWNER_FIELD_ERROR, ownerEmailError, ownerPhoneError, validateOwnerForm } from '../src/features/users/ownerForm.ts';
import {
  isUnsafeApiMessage,
  safeApiErrorMessage,
  validateAmount,
  validateEmail,
  validatePhone,
  validatePrice,
  validateRequiredText,
} from '../src/lib/validation.ts';

describe('phone validation', () => {
  it('accepts +91, 91, and 10-digit Indian mobiles', () => {
    assert.equal(validatePhone('+919876543210'), null);
    assert.equal(validatePhone('919876543210'), null);
    assert.equal(validatePhone('9876543210'), null);
    assert.equal(validatePhone('+91 98765 43210'), null);
    assert.equal(validatePhone(''), null);
  });

  it('rejects invalid phone values', () => {
    assert.match(validatePhone('+91abc1234567') ?? '', /valid Indian phone/);
    assert.match(validatePhone('+91987654321') ?? '', /valid Indian phone/);
    assert.match(validatePhone('+9198765432100') ?? '', /valid Indian phone/);
    assert.match(validatePhone('1234567890') ?? '', /valid Indian phone/);
    assert.match(validatePhone('phone!') ?? '', /valid Indian phone/);
    assert.equal(ownerPhoneError('+91abc1234567'), ownerPhoneError('bad'));
  });
});

describe('email and required text', () => {
  it('validates email consistently with Observation #12', () => {
    assert.equal(validateEmail('owner@realstick.in', true), null);
    assert.equal(validateEmail('not-an-email', true), 'Invalid email format.');
    assert.equal(ownerEmailError(''), OWNER_FIELD_ERROR.emailRequired);
    assert.equal(ownerEmailError('bad'), OWNER_FIELD_ERROR.emailInvalid);
  });

  it('rejects blank required text after trim', () => {
    assert.equal(validateRequiredText('  Outlet  '), null);
    assert.equal(validateRequiredText('   ', 'Outlet name is required'), 'Outlet name is required');
    const errors = validateOwnerForm(
      { full_name: '   ', email: '', phone: '', role: 'SYSTEM_ADMIN', franchise_id: '' },
    );
    assert.equal(errors.full_name, OWNER_FIELD_ERROR.nameRequired);
  });
});

describe('price and amount validation', () => {
  it('accepts valid currency amounts', () => {
    assert.equal(validatePrice('100', { allowZero: true, requirePositive: false }), null);
    assert.equal(validatePrice('100.50', { allowZero: true, requirePositive: false }), null);
    assert.equal(validateAmount('250.50'), null);
    assert.equal(sellingPriceError('80'), null);
    assert.equal(paidAmountError('1500.25'), null);
  });

  it('rejects malformed, negative, and over-precise money', () => {
    assert.equal(validatePrice('100.123', { allowZero: true, requirePositive: false }), 'Enter a valid price with up to 2 decimal places.');
    assert.equal(validatePrice('abc', { allowZero: true, requirePositive: false }), 'Enter a valid price with up to 2 decimal places.');
    assert.equal(validateAmount('-100'), 'Enter a valid amount with up to 2 decimal places.');
    assert.equal(validateAmount('0'), 'Amount must be greater than 0.');
    assert.equal(sellingPriceError('0'), 'Selling price must be greater than 0.');
    assert.equal(paidAmountError('100.123'), 'Enter a valid amount with up to 2 decimal places.');
  });
});

describe('safe API error messages', () => {
  it('keeps business errors and hides technical text', () => {
    assert.equal(
      safeApiErrorMessage(
        { response: { data: { detail: 'This franchise cannot be deleted because it is already used in existing business records. Deactivate it instead.' } } },
        'fallback',
      ),
      'This franchise cannot be deleted because it is already used in existing business records. Deactivate it instead.',
    );
    assert.equal(isUnsafeApiMessage('AxiosError: Request failed with status code 500'), true);
    assert.equal(isUnsafeApiMessage('duplicate key value violates unique constraint'), true);
    assert.equal(
      safeApiErrorMessage({ message: 'Request failed with status code 409' }, 'Unable to delete franchise.'),
      'Unable to delete franchise.',
    );
  });
});
