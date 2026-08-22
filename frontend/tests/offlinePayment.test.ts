import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  applyOfflinePaymentSaveResult,
  emptyOfflinePaymentForm,
  paidAmountError,
  paymentDateError,
  paymentMethodError,
  paymentStateLabel,
  todayIsoDate,
  toOfflinePaymentPayload,
  validateOfflinePaymentForm,
} from '../src/features/franchises/offlinePayment.ts';

const root = dirname(fileURLToPath(import.meta.url));

describe('offline payment form validation', () => {
  it('rejects missing required fields', () => {
    const errors = validateOfflinePaymentForm({
      amount: '',
      paidAt: '',
      paymentMethod: '',
      referenceNumber: '',
      notes: '',
    });
    assert.equal(errors.amount, 'Paid amount is required.');
    assert.equal(errors.paidAt, 'Payment date is required.');
    assert.equal(errors.paymentMethod, 'Payment method is required.');
  });

  it('rejects invalid amounts without rounding them', () => {
    assert.equal(paidAmountError('0'), 'Paid amount must be greater than 0.');
    assert.equal(paidAmountError('-10'), 'Enter a valid amount with up to 2 decimal places.');
    assert.equal(paidAmountError('12.345'), 'Enter a valid amount with up to 2 decimal places.');
    assert.equal(paidAmountError('abc'), 'Enter a valid amount with up to 2 decimal places.');
    assert.equal(paidAmountError('100.50'), null);
    assert.equal(paidAmountError('1'), null);
  });

  it('rejects invalid dates and methods', () => {
    assert.equal(paymentDateError('2026-13-01'), 'Enter a valid payment date.');
    assert.equal(paymentDateError('2026-02-31'), 'Enter a valid payment date.');
    assert.equal(paymentDateError('2026-08-21'), null);
    assert.equal(paymentMethodError('CARD'), 'Select a valid payment method.');
    assert.equal(paymentMethodError('BANK_TRANSFER'), null);
  });

  it('builds an API payload using ISO dates rather than locale formatting', () => {
    const payload = toOfflinePaymentPayload({
      amount: '250000.50',
      paidAt: '2026-08-20',
      paymentMethod: 'UPI',
      referenceNumber: ' UPI-12 ',
      notes: ' Head office ',
    });
    assert.deepEqual(payload, {
      amount: 250000.5,
      paid_at: '2026-08-20',
      payment_method: 'UPI',
      reference_number: 'UPI-12',
      notes: 'Head office',
    });
  });

  it('defaults the payment date to the current local calendar date', () => {
    assert.equal(todayIsoDate(new Date(2026, 7, 21, 23, 15)), '2026-08-21');
    assert.equal(emptyOfflinePaymentForm(new Date(2026, 0, 2)).paidAt, '2026-01-02');
  });
});

describe('offline payment save feedback', () => {
  it('closes the dialog after a successful save', () => {
    assert.deepEqual(applyOfflinePaymentSaveResult(true), { dialogOpen: false, error: null });
  });

  it('keeps the dialog open and surfaces an error after a failed save', () => {
    assert.deepEqual(applyOfflinePaymentSaveResult(false, 'Unable to record franchise payment'), {
      dialogOpen: true,
      error: 'Unable to record franchise payment',
    });
  });
});

describe('payment state labels', () => {
  it('uses existing franchise_payments status values', () => {
    assert.equal(paymentStateLabel('COMPLETED'), 'Completed');
    assert.equal(paymentStateLabel('PENDING'), 'Pending');
    assert.equal(paymentStateLabel(null), 'Not recorded');
  });
});

describe('Record Offline Payment UI', () => {
  const dialog = readFileSync(join(root, '../src/features/franchises/RecordOfflinePaymentDialog.tsx'), 'utf8');
  const page = readFileSync(join(root, '../src/features/franchises/FranchiseDetailPage.tsx'), 'utf8');

  it('renders the offline payment dialog fields', () => {
    assert.equal(dialog.includes('Record Offline Payment'), true);
    assert.equal(dialog.includes('Paid Amount'), true);
    assert.equal(dialog.includes('Payment Date'), true);
    assert.equal(dialog.includes('Payment Method'), true);
    assert.equal(dialog.includes('Payment Reference'), true);
    assert.equal(dialog.includes('Admin recording of a franchise payment'), true);
  });

  it('closes the dialog after success and keeps it open after failure', () => {
    const successBlock = dialog.slice(dialog.indexOf('onSuccess'), dialog.indexOf('onError'));
    const errorBlock = dialog.slice(dialog.indexOf('onError'), dialog.indexOf('function update'));
    assert.equal(successBlock.includes('onClose()'), true);
    assert.equal(errorBlock.includes('onClose()'), false);
    assert.equal(errorBlock.includes('setError'), true);
    assert.equal(dialog.includes('Unable to record the offline payment.'), true);
  });

  it('refreshes franchise, launch-progress, and payment-history data after a successful save', () => {
    assert.equal(page.includes('handlePaymentSaved'), true);
    assert.equal(page.includes("queryClient.setQueryData(['admin-franchise', franchiseId], updated)"), true);
    assert.equal(page.includes("invalidateQueries({ queryKey: ['admin-franchise', franchiseId] })"), true);
    assert.equal(page.includes('LaunchProgressTrack'), true);
    assert.equal(page.includes('payment_status: franchise.payment_status'), true);
    assert.equal(page.includes('PaymentHistorySection'), true);
    assert.equal(page.includes('payments={franchise.payments}'), true);
  });
});
