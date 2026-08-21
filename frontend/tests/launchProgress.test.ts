import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  deriveLaunchProgress,
  isPaymentReceived,
  isReadyToLaunch,
} from '../src/features/franchises/launchStages.ts';
import type { FranchiseStatus } from '../src/types/franchise.ts';

function progress(status: FranchiseStatus, payment_status: string | null = null) {
  return deriveLaunchProgress({ status, payment_status });
}

function states(status: FranchiseStatus, payment_status: string | null = null) {
  return progress(status, payment_status).stages.map((stage) => stage.state);
}

describe('isPaymentReceived', () => {
  it('treats COMPLETED franchise_payments status as received', () => {
    assert.equal(isPaymentReceived('COMPLETED'), true);
  });

  it('does not treat missing or non-completed payment rows as received', () => {
    assert.equal(isPaymentReceived(null), false);
    assert.equal(isPaymentReceived(undefined), false);
    assert.equal(isPaymentReceived('PENDING'), false);
    assert.equal(isPaymentReceived('FAILED'), false);
    assert.equal(isPaymentReceived('REFUNDED'), false);
  });
});

describe('isReadyToLaunch', () => {
  it('uses ACTIVE as the operational ready state', () => {
    assert.equal(isReadyToLaunch('ACTIVE'), true);
  });

  it('treats post-launch SUSPENDED and CLOSED as having passed ready-to-launch', () => {
    assert.equal(isReadyToLaunch('SUSPENDED'), true);
    assert.equal(isReadyToLaunch('CLOSED'), true);
  });

  it('does not treat pre-launch franchise statuses as ready', () => {
    assert.equal(isReadyToLaunch('SETUP'), false);
    assert.equal(isReadyToLaunch('PENDING_PAYMENT'), false);
    assert.equal(isReadyToLaunch('APPLICATION'), false);
  });
});

describe('deriveLaunchProgress', () => {
  it('always marks Franchise Created complete for an existing franchise', () => {
    const derived = progress('SETUP');
    assert.equal(derived.stages[0].label, 'Franchise Created');
    assert.equal(derived.stages[0].state, 'completed');
    assert.equal(derived.totalCount, 3);
  });

  it('keeps stages sequential for a new franchise with no payment', () => {
    assert.deepEqual(states('SETUP'), ['completed', 'current', 'pending']);
    assert.equal(progress('SETUP').currentLabel, 'Payment Received');
    assert.equal(progress('SETUP').completedCount, 1);
    assert.equal(progress('SETUP').allComplete, false);
  });

  it('ACTIVE + no completed payment stays on Payment Received; Ready stays pending', () => {
    const derived = progress('ACTIVE');
    assert.deepEqual(states('ACTIVE'), ['completed', 'current', 'pending']);
    assert.equal(derived.stages[1].state, 'current');
    assert.equal(derived.stages[2].state, 'pending');
    assert.equal(derived.currentLabel, 'Payment Received');
    assert.equal(derived.allComplete, false);
  });

  it('ACTIVE + completed payment marks all three stages complete', () => {
    const derived = progress('ACTIVE', 'COMPLETED');
    assert.deepEqual(states('ACTIVE', 'COMPLETED'), ['completed', 'completed', 'completed']);
    assert.equal(derived.allComplete, true);
    assert.equal(derived.currentLabel, 'Ready to Launch');
    assert.equal(derived.completedCount, 3);
  });

  it('SETUP + completed payment completes Payment and keeps Ready current', () => {
    assert.deepEqual(states('SETUP', 'COMPLETED'), ['completed', 'completed', 'current']);
    assert.equal(progress('SETUP', 'COMPLETED').currentLabel, 'Ready to Launch');
    assert.equal(progress('SETUP', 'COMPLETED').completedCount, 2);
    assert.equal(progress('SETUP', 'COMPLETED').allComplete, false);
  });

  it('SUSPENDED + completed payment marks Ready to Launch complete', () => {
    assert.deepEqual(states('SUSPENDED', 'COMPLETED'), ['completed', 'completed', 'completed']);
    assert.equal(progress('SUSPENDED', 'COMPLETED').allComplete, true);
  });

  it('CLOSED + completed payment marks Ready to Launch complete', () => {
    assert.deepEqual(states('CLOSED', 'COMPLETED'), ['completed', 'completed', 'completed']);
    assert.equal(progress('CLOSED', 'COMPLETED').allComplete, true);
  });

  it('SUSPENDED or CLOSED without payment cannot complete Ready to Launch', () => {
    assert.deepEqual(states('SUSPENDED'), ['completed', 'current', 'pending']);
    assert.deepEqual(states('CLOSED'), ['completed', 'current', 'pending']);
  });

  it('keeps PENDING_PAYMENT outlets on the payment stage until a completed payment exists', () => {
    assert.deepEqual(states('PENDING_PAYMENT'), ['completed', 'current', 'pending']);
    assert.deepEqual(states('PENDING_PAYMENT', 'COMPLETED'), ['completed', 'completed', 'current']);
  });

  it('exposes business labels rather than checklist item names', () => {
    const labels = progress('SETUP').stages.map((stage) => stage.label);
    assert.deepEqual(labels, ['Franchise Created', 'Payment Received', 'Ready to Launch']);
  });
});

describe('Franchise Detail hidden sections', () => {
  const page = readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), '../src/features/franchises/FranchiseDetailPage.tsx'),
    'utf8',
  );

  it('does not render the Franchise Application section', () => {
    assert.equal(page.includes('Franchise Application'), false);
    assert.equal(page.includes('franchise.applications'), false);
  });

  it('does not restore the old Payment Status section', () => {
    assert.equal(page.includes('Payment Status'), false);
  });

  it('does not restore the old 8-step launch checklist', () => {
    assert.equal(page.includes('launch_checklist'), false);
    assert.equal(page.includes('Franchise agreement signed'), false);
  });

  it('keeps Launch Progress and product assignment as the primary detail sections', () => {
    assert.equal(page.includes('LaunchProgressTrack'), true);
    assert.equal(page.includes('FranchiseProductsPanel'), true);
  });

  it('exposes Record Offline Payment and Payment History without restoring the old payment table', () => {
    assert.equal(page.includes('RecordOfflinePaymentDialog'), true);
    assert.equal(page.includes('PaymentHistorySection'), true);
    assert.equal(page.includes('payments={franchise.payments}'), true);
  });
});
