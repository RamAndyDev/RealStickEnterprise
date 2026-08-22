import { useMutation } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';

import { Button, ErrorBanner, Field, Modal, SelectField } from '../../components/ui';
import { recordOfflineFranchisePayment } from '../../lib/franchisesApi';
import type { FranchiseDetail, FranchisePaymentMethod } from '../../types/franchise';
import {
  FRANCHISE_PAYMENT_METHODS,
  FRANCHISE_PAYMENT_METHOD_LABELS,
  applyOfflinePaymentSaveResult,
  emptyOfflinePaymentForm,
  paymentStateLabel,
  toOfflinePaymentPayload,
  validateOfflinePaymentForm,
  type OfflinePaymentForm,
} from './offlinePayment';
import { apiErrorMessage } from './status';

type RecordOfflinePaymentDialogProps = {
  franchiseId: string;
  paymentStatus: string | null | undefined;
  onClose: () => void;
  onSaved: (franchise: FranchiseDetail) => void;
};

export function RecordOfflinePaymentDialog({
  franchiseId,
  paymentStatus,
  onClose,
  onSaved,
}: RecordOfflinePaymentDialogProps) {
  const [form, setForm] = useState<OfflinePaymentForm>(() => emptyOfflinePaymentForm());
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const saveMutation = useMutation({
    mutationFn: () => recordOfflineFranchisePayment(franchiseId, toOfflinePaymentPayload(form)),
    onSuccess: (franchise) => {
      const result = applyOfflinePaymentSaveResult(true);
      setError(result.error);
      onSaved(franchise);
      onClose();
    },
    onError: (err) => {
      const result = applyOfflinePaymentSaveResult(
        false,
        apiErrorMessage(err, 'Unable to record the offline payment.'),
      );
      setError(result.error);
    },
  });

  function update<K extends keyof OfflinePaymentForm>(key: K, value: OfflinePaymentForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const errors = validateOfflinePaymentForm(form);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      setError(null);
      return;
    }
    saveMutation.mutate();
  }

  return (
    <Modal
      title="Record Offline Payment"
      subtitle="Admin recording of a franchise payment received outside the online flow."
      onClose={onClose}
      footer={
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="muted" onClick={onClose} disabled={saveMutation.isPending}>
            Cancel
          </Button>
          <Button type="submit" form="offline-payment-form" disabled={saveMutation.isPending}>
            {saveMutation.isPending ? 'Saving…' : 'Save Payment'}
          </Button>
        </div>
      }
    >
      <p className="mb-3 text-sm text-[#5C5C56]">
        Current payment: <span className="font-semibold text-[#1A1A18]">{paymentStateLabel(paymentStatus)}</span>
      </p>
      {error ? (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      ) : null}
      <form id="offline-payment-form" onSubmit={handleSubmit}>
        <Field
          label="Paid Amount (INR)"
          name="amount"
          inputMode="decimal"
          value={form.amount}
          onChange={(event) => update('amount', event.target.value)}
          error={fieldErrors.amount}
          placeholder="0.00"
          required
        />
        <Field
          label="Payment Date"
          name="paidAt"
          type="date"
          value={form.paidAt}
          onChange={(event) => update('paidAt', event.target.value)}
          error={fieldErrors.paidAt}
          required
        />
        <SelectField
          label="Payment Method"
          name="paymentMethod"
          value={form.paymentMethod}
          onChange={(event) => update('paymentMethod', event.target.value as FranchisePaymentMethod | '')}
          error={fieldErrors.paymentMethod}
          required
        >
          <option value="">Select method</option>
          {FRANCHISE_PAYMENT_METHODS.map((method) => (
            <option key={method} value={method}>
              {FRANCHISE_PAYMENT_METHOD_LABELS[method]}
            </option>
          ))}
        </SelectField>
        <Field
          label="Payment Reference (optional)"
          name="referenceNumber"
          value={form.referenceNumber}
          onChange={(event) => update('referenceNumber', event.target.value)}
          placeholder="UTR, cheque no., or receipt no."
        />
        <label className="mb-3 block">
          <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
            Remarks (optional)
          </span>
          <textarea
            name="notes"
            className="min-h-[80px] w-full rounded-lg border border-[#E0DDD5] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1A7A4A]"
            value={form.notes}
            onChange={(event) => update('notes', event.target.value)}
            placeholder="Optional notes about this offline payment"
          />
        </label>
      </form>
    </Modal>
  );
}
