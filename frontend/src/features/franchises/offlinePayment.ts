import type {
  FranchiseOfflinePaymentPayload,
  FranchisePayment,
  FranchisePaymentMethod,
} from '../../types/franchise';

export const FRANCHISE_PAYMENT_METHODS: FranchisePaymentMethod[] = [
  'CASH',
  'BANK_TRANSFER',
  'UPI',
  'CHEQUE',
  'OTHER',
];

export type OfflinePaymentForm = {
  amount: string;
  paidAt: string;
  paymentMethod: FranchisePaymentMethod | '';
  referenceNumber: string;
  notes: string;
};

export const FRANCHISE_PAYMENT_METHOD_LABELS: Record<FranchisePaymentMethod, string> = {
  CASH: 'Cash',
  BANK_TRANSFER: 'Bank Transfer',
  UPI: 'UPI',
  CHEQUE: 'Cheque',
  OTHER: 'Other',
};

export function emptyOfflinePaymentForm(now = new Date()): OfflinePaymentForm {
  return {
    amount: '',
    paidAt: todayIsoDate(now),
    paymentMethod: '',
    referenceNumber: '',
    notes: '',
  };
}

export function todayIsoDate(now = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function paidAmountError(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return 'Paid amount is required.';
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) {
    return 'Enter a valid amount with up to 2 decimal places.';
  }
  const amount = Number(trimmed);
  if (Number.isNaN(amount) || amount <= 0) {
    return 'Paid amount must be greater than 0.';
  }
  return null;
}

export function paymentDateError(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return 'Payment date is required.';
  if (!/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return 'Enter a valid payment date.';
  }
  const [year, month, day] = trimmed.split('-').map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== day
  ) {
    return 'Enter a valid payment date.';
  }
  return null;
}

export function paymentMethodError(value: string): string | null {
  if (!value) return 'Payment method is required.';
  if (!FRANCHISE_PAYMENT_METHODS.includes(value as FranchisePaymentMethod)) {
    return 'Select a valid payment method.';
  }
  return null;
}

export function validateOfflinePaymentForm(form: OfflinePaymentForm): Record<string, string> {
  const errors: Record<string, string> = {};
  const amount = paidAmountError(form.amount);
  const paidAt = paymentDateError(form.paidAt);
  const paymentMethod = paymentMethodError(form.paymentMethod);
  if (amount) errors.amount = amount;
  if (paidAt) errors.paidAt = paidAt;
  if (paymentMethod) errors.paymentMethod = paymentMethod;
  return errors;
}

export function toOfflinePaymentPayload(form: OfflinePaymentForm): FranchiseOfflinePaymentPayload {
  return {
    amount: Number(form.amount.trim()),
    paid_at: form.paidAt.trim(),
    payment_method: form.paymentMethod as FranchisePaymentMethod,
    reference_number: form.referenceNumber.trim() || null,
    notes: form.notes.trim() || null,
  };
}

export function paymentStateLabel(status: string | null | undefined): string {
  if (status === 'COMPLETED') return 'Completed';
  if (status === 'PENDING') return 'Pending';
  if (status === 'FAILED') return 'Failed';
  if (status === 'REFUNDED') return 'Refunded';
  return 'Not recorded';
}

export function applyOfflinePaymentSaveResult(
  saveSucceeded: boolean,
  errorMessage?: string,
): { dialogOpen: boolean; error: string | null } {
  if (saveSucceeded) {
    return { dialogOpen: false, error: null };
  }
  return {
    dialogOpen: true,
    error: errorMessage || 'Unable to record the offline payment.',
  };
}

export type PaymentHistoryRow = {
  id: string;
  dateLabel: string;
  amountLabel: string;
  methodLabel: string;
  reference: string;
  status: string;
  statusLabel: string;
  statusTone: 'green' | 'orange' | 'muted' | 'red' | 'amber';
  remarks: string;
};

export type PaymentHistoryView = {
  rows: PaymentHistoryRow[];
  totalPaid: number;
  totalPaidLabel: string;
  latestDateLabel: string;
  latestStatus: string | null;
  latestStatusLabel: string;
  latestStatusTone: PaymentHistoryRow['statusTone'];
};

function paymentTime(value: string | null | undefined): number {
  if (!value) return 0;
  const time = Date.parse(value);
  return Number.isNaN(time) ? 0 : time;
}

function comparePaymentsNewestFirst(a: FranchisePayment, b: FranchisePayment): number {
  const paidDiff = paymentTime(b.paid_at) - paymentTime(a.paid_at);
  if (paidDiff !== 0) return paidDiff;
  const createdDiff = paymentTime(b.created_at) - paymentTime(a.created_at);
  if (createdDiff !== 0) return createdDiff;
  return String(b.id).localeCompare(String(a.id));
}

export function sortPaymentHistory(payments: FranchisePayment[]): FranchisePayment[] {
  return payments.slice().sort(comparePaymentsNewestFirst);
}

export function isCompletedPayment(status: string | null | undefined): boolean {
  return status === 'COMPLETED';
}

export function totalPaidAmount(payments: FranchisePayment[]): number {
  return payments.reduce((sum, payment) => {
    if (!isCompletedPayment(payment.status)) return sum;
    const amount = Number(payment.amount);
    return Number.isFinite(amount) ? sum + amount : sum;
  }, 0);
}

export function formatPaymentAmount(amount: number): string {
  return `₹${amount.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatPaymentDate(value: string | null | undefined): string {
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function paymentMethodLabel(method: string | null | undefined): string {
  if (!method) return '—';
  if (FRANCHISE_PAYMENT_METHODS.includes(method as FranchisePaymentMethod)) {
    return FRANCHISE_PAYMENT_METHOD_LABELS[method as FranchisePaymentMethod];
  }
  return method;
}

export function paymentStatusTone(status: string | null | undefined): PaymentHistoryRow['statusTone'] {
  switch (status) {
    case 'COMPLETED':
      return 'green';
    case 'PENDING':
      return 'orange';
    case 'FAILED':
      return 'red';
    case 'REFUNDED':
      return 'muted';
    default:
      return 'amber';
  }
}

export function paymentRowStatusLabel(status: string | null | undefined): string {
  if (!status) return '—';
  if (status === 'COMPLETED' || status === 'PENDING' || status === 'FAILED' || status === 'REFUNDED') {
    return paymentStateLabel(status);
  }
  return status.replaceAll('_', ' ');
}

export function buildPaymentHistory(payments: FranchisePayment[]): PaymentHistoryView {
  const rows = sortPaymentHistory(payments).map((payment) => ({
    id: payment.id,
    dateLabel: formatPaymentDate(payment.paid_at || payment.created_at),
    amountLabel: formatPaymentAmount(Number(payment.amount) || 0),
    methodLabel: paymentMethodLabel(payment.payment_method),
    reference: payment.reference_number?.trim() || '—',
    status: payment.status,
    statusLabel: paymentRowStatusLabel(payment.status),
    statusTone: paymentStatusTone(payment.status),
    remarks: payment.notes?.trim() || '—',
  }));
  const totalPaid = totalPaidAmount(payments);
  const latest = rows[0] ?? null;

  return {
    rows,
    totalPaid,
    totalPaidLabel: formatPaymentAmount(totalPaid),
    latestDateLabel: latest?.dateLabel ?? '—',
    latestStatus: latest?.status ?? null,
    latestStatusLabel: latest ? latest.statusLabel : paymentStateLabel(null),
    latestStatusTone: latest ? latest.statusTone : 'muted',
  };
}
