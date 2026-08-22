import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import type { FranchisePayment } from '../src/types/franchise.ts';
import {
  buildPaymentHistory,
  formatPaymentAmount,
  paymentMethodLabel,
  paymentRowStatusLabel,
  paymentStatusTone,
  totalPaidAmount,
} from '../src/features/franchises/offlinePayment.ts';

const root = dirname(fileURLToPath(import.meta.url));

function payment(overrides: Partial<FranchisePayment> & Pick<FranchisePayment, 'id'>): FranchisePayment {
  return {
    amount: 10000,
    currency: 'INR',
    payment_method: 'UPI',
    reference_number: 'UPI-12345',
    status: 'COMPLETED',
    paid_at: '2026-08-21T12:00:00.000Z',
    notes: 'Initial payment',
    created_at: '2026-08-21T12:00:00.000Z',
    updated_at: '2026-08-21T12:00:00.000Z',
    ...overrides,
  };
}

describe('payment history records', () => {
  it('renders existing payment records with method, reference, remarks, and status', () => {
    const history = buildPaymentHistory([
      payment({
        id: 'p1',
        amount: 10000,
        payment_method: 'UPI',
        reference_number: 'UPI-12345',
        notes: 'Initial payment',
        status: 'COMPLETED',
      }),
    ]);

    assert.equal(history.rows.length, 1);
    assert.equal(history.rows[0].amountLabel, formatPaymentAmount(10000));
    assert.equal(history.rows[0].methodLabel, 'UPI');
    assert.equal(history.rows[0].reference, 'UPI-12345');
    assert.equal(history.rows[0].remarks, 'Initial payment');
    assert.equal(history.rows[0].statusLabel, 'Completed');
    assert.equal(history.rows[0].statusTone, 'green');
  });

  it('returns an empty history when no payments exist', () => {
    const history = buildPaymentHistory([]);
    assert.equal(history.rows.length, 0);
    assert.equal(history.totalPaid, 0);
    assert.equal(history.latestDateLabel, '—');
    assert.equal(history.latestStatusLabel, 'Not recorded');
  });

  it('displays multiple payments with the newest paid_at first', () => {
    const history = buildPaymentHistory([
      payment({
        id: 'older',
        paid_at: '2026-08-10T12:00:00.000Z',
        created_at: '2026-08-20T12:00:00.000Z',
        amount: 4000,
      }),
      payment({
        id: 'newer',
        paid_at: '2026-08-21T12:00:00.000Z',
        created_at: '2026-08-11T12:00:00.000Z',
        amount: 6000,
        payment_method: 'BANK_TRANSFER',
        reference_number: 'NEFT-9',
      }),
      payment({
        id: 'middle',
        paid_at: '2026-08-15T12:00:00.000Z',
        amount: 2000,
        payment_method: 'CASH',
        reference_number: null,
        notes: null,
      }),
    ]);

    assert.deepEqual(
      history.rows.map((row) => row.id),
      ['newer', 'middle', 'older'],
    );
    assert.equal(history.rows[0].methodLabel, 'Bank Transfer');
    assert.equal(history.rows[1].methodLabel, 'Cash');
    assert.equal(history.rows[1].reference, '—');
    assert.equal(history.rows[1].remarks, '—');
    assert.equal(history.latestStatus, 'COMPLETED');
  });

  it('uses created_at then id when paid_at values are the same', () => {
    const history = buildPaymentHistory([
      payment({
        id: 'a',
        paid_at: '2026-08-21T12:00:00.000Z',
        created_at: '2026-08-21T10:00:00.000Z',
      }),
      payment({
        id: 'b',
        paid_at: '2026-08-21T12:00:00.000Z',
        created_at: '2026-08-21T11:00:00.000Z',
      }),
    ]);
    assert.deepEqual(
      history.rows.map((row) => row.id),
      ['b', 'a'],
    );
  });

  it('formats amounts with two decimal places', () => {
    const formatted = formatPaymentAmount(10000);
    assert.equal(formatted.startsWith('₹'), true);
    assert.equal(formatted.endsWith('00'), true);
    assert.match(formatted, /10[,.]?000\.00/);
    assert.match(formatPaymentAmount(250000.5), /250[,.]?000\.50|2,50,000\.50/);
  });
});

describe('payment history totals', () => {
  it('counts only COMPLETED payments toward Total Paid', () => {
    const payments = [
      payment({ id: 'paid', amount: 10000, status: 'COMPLETED' }),
      payment({ id: 'pending', amount: 5000, status: 'PENDING' }),
      payment({ id: 'failed', amount: 2000, status: 'FAILED' }),
      payment({ id: 'refunded', amount: 1500, status: 'REFUNDED' }),
      payment({ id: 'second', amount: 2500.5, status: 'COMPLETED' }),
    ];

    assert.equal(totalPaidAmount(payments), 12500.5);
    const history = buildPaymentHistory(payments);
    assert.equal(history.totalPaid, 12500.5);
    assert.equal(history.totalPaidLabel, formatPaymentAmount(12500.5));
  });

  it('does not treat FAILED or REFUNDED payments as paid', () => {
    assert.equal(
      totalPaidAmount([
        payment({ id: 'failed', amount: 9999, status: 'FAILED' }),
        payment({ id: 'refunded', amount: 8888, status: 'REFUNDED' }),
      ]),
      0,
    );
  });
});

describe('payment history status and methods', () => {
  it('maps existing franchise payment statuses to badges', () => {
    assert.equal(paymentRowStatusLabel('COMPLETED'), 'Completed');
    assert.equal(paymentRowStatusLabel('PENDING'), 'Pending');
    assert.equal(paymentRowStatusLabel('FAILED'), 'Failed');
    assert.equal(paymentRowStatusLabel('REFUNDED'), 'Refunded');
    assert.equal(paymentStatusTone('COMPLETED'), 'green');
    assert.equal(paymentStatusTone('PENDING'), 'orange');
    assert.equal(paymentStatusTone('FAILED'), 'red');
    assert.equal(paymentStatusTone('REFUNDED'), 'muted');
  });

  it('uses franchise payment method labels rather than POS methods', () => {
    assert.equal(paymentMethodLabel('CASH'), 'Cash');
    assert.equal(paymentMethodLabel('BANK_TRANSFER'), 'Bank Transfer');
    assert.equal(paymentMethodLabel('UPI'), 'UPI');
    assert.equal(paymentMethodLabel('CHEQUE'), 'Cheque');
    assert.equal(paymentMethodLabel('OTHER'), 'Other');
  });
});

describe('Payment History UI', () => {
  const section = readFileSync(join(root, '../src/features/franchises/PaymentHistorySection.tsx'), 'utf8');
  const page = readFileSync(join(root, '../src/features/franchises/FranchiseDetailPage.tsx'), 'utf8');
  const launch = readFileSync(join(root, '../src/features/franchises/launchStages.ts'), 'utf8');
  const dialog = readFileSync(join(root, '../src/features/franchises/RecordOfflinePaymentDialog.tsx'), 'utf8');

  it('renders Payment History with the expected columns and empty state', () => {
    assert.equal(section.includes('Payment History'), true);
    assert.equal(section.includes('>Date</th>'), true);
    assert.equal(section.includes('>Amount</th>'), true);
    assert.equal(section.includes('Payment Method'), true);
    assert.equal(section.includes('>Reference</th>'), true);
    assert.equal(section.includes('>Status</th>'), true);
    assert.equal(section.includes('>Remarks</th>'), true);
    assert.equal(section.includes('No payments recorded yet.'), true);
    assert.equal(section.includes('overflow-x-auto'), true);
    assert.equal(section.includes('Record Offline Payment'), true);
    assert.equal(section.includes('Unable to load payment history.'), true);
  });

  it('shows summary totals without inventing extra financial rules', () => {
    assert.equal(section.includes('Total Paid'), true);
    assert.equal(section.includes('Latest Payment Date'), true);
    assert.equal(section.includes('Latest Payment Status'), true);
  });

  it('refreshes history from franchise detail after recording a payment', () => {
    assert.equal(page.includes('PaymentHistorySection'), true);
    assert.equal(page.includes('payments={franchise.payments}'), true);
    assert.equal(page.includes('handlePaymentSaved'), true);
    assert.equal(page.includes("queryClient.setQueryData(['admin-franchise', franchiseId], updated)"), true);
  });

  it('keeps Record Offline Payment dialog behavior unchanged', () => {
    assert.equal(dialog.includes('Record Offline Payment'), true);
    assert.equal(dialog.includes('Paid Amount'), true);
    const successBlock = dialog.slice(dialog.indexOf('onSuccess'), dialog.indexOf('onError'));
    const errorBlock = dialog.slice(dialog.indexOf('onError'), dialog.indexOf('function update'));
    assert.equal(successBlock.includes('onClose()'), true);
    assert.equal(errorBlock.includes('onClose()'), false);
  });

  it('does not restore hidden Observation #4 sections or change Launch Progress logic', () => {
    assert.equal(page.includes('Franchise Application'), false);
    assert.equal(page.includes('Payment Status'), false);
    assert.equal(page.includes('launch_checklist'), false);
    assert.equal(page.includes('LaunchProgressTrack'), true);
    assert.equal(launch.includes("key: 'created'"), true);
    assert.equal(launch.includes("key: 'payment'"), true);
    assert.equal(launch.includes("key: 'ready'"), true);
    assert.equal(launch.includes('paymentStatus === \'COMPLETED\''), true);
  });
});
