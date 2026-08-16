export type FranchiseAuditStatus = 'PASS' | 'NEEDS_ATTENTION' | 'FAIL';

export type ChecklistDefinition = {
  item_key: string;
  label: string;
  display_order: number;
};

/** Mirrors the backend FRANCHISE_OPERATIONAL_CHECKLIST. Backend remains authoritative. */
export const FRANCHISE_OPERATIONAL_CHECKLIST: ChecklistDefinition[] = [
  { item_key: 'pos_working', label: 'POS system working', display_order: 1 },
  { item_key: 'internet_working', label: 'Internet connection working', display_order: 2 },
  { item_key: 'receipt_printer_working', label: 'Receipt printer working', display_order: 3 },
  { item_key: 'product_menu_correct', label: 'Product/menu information correct', display_order: 4 },
  { item_key: 'selling_prices_correct', label: 'Product selling prices correct', display_order: 5 },
  { item_key: 'product_availability_correct', label: 'Product availability correct', display_order: 6 },
  { item_key: 'billing_process_working', label: 'Billing process working', display_order: 7 },
  { item_key: 'payment_methods_working', label: 'Payment methods working', display_order: 8 },
  { item_key: 'store_presentation', label: 'Store/product presentation satisfactory', display_order: 9 },
  { item_key: 'general_operation', label: 'General cleanliness/operation satisfactory', display_order: 10 },
];

export type AuditItem = {
  id: string;
  item_key: string;
  checklist_item: string;
  display_order: number;
  status: FranchiseAuditStatus;
  remarks: string | null;
};

export type AuditListItem = {
  id: string;
  franchise_id: string;
  franchise_name: string;
  audit_date: string;
  auditor_id: string | null;
  auditor_name: string;
  overall_status: FranchiseAuditStatus;
  created_at: string;
};

export type AuditListResponse = {
  items: AuditListItem[];
  page: number;
  page_size: number;
  total: number;
};

export type AuditListParams = {
  franchise_id?: string;
  from_date?: string;
  to_date?: string;
  overall_status?: FranchiseAuditStatus | '';
  page?: number;
  page_size?: number;
};

export type AuditDetail = {
  id: string;
  franchise_id: string;
  franchise_name: string;
  audit_date: string;
  auditor_id: string | null;
  auditor_name: string;
  overall_status: FranchiseAuditStatus;
  remarks: string | null;
  created_at: string;
  updated_at: string;
  items: AuditItem[];
};

export type AuditItemWrite = {
  item_key: string;
  status: FranchiseAuditStatus;
  remarks?: string | null;
};

export type AuditCreatePayload = {
  franchise_id?: string;
  audit_date: string;
  remarks?: string | null;
  items: AuditItemWrite[];
};

export function utcTodayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function calculateOverallStatus(
  statuses: Array<FranchiseAuditStatus | ''>,
): FranchiseAuditStatus | null {
  const selected = statuses.filter((value): value is FranchiseAuditStatus => Boolean(value));
  if (selected.length === 0) return null;
  if (selected.some((value) => value === 'FAIL')) return 'FAIL';
  if (selected.some((value) => value === 'NEEDS_ATTENTION')) return 'NEEDS_ATTENTION';
  return 'PASS';
}

export function auditStatusTone(
  status: FranchiseAuditStatus,
): 'green' | 'amber' | 'red' {
  if (status === 'PASS') return 'green';
  if (status === 'NEEDS_ATTENTION') return 'amber';
  return 'red';
}

export function auditStatusLabel(status: FranchiseAuditStatus): string {
  if (status === 'NEEDS_ATTENTION') return 'NEEDS ATTENTION';
  return status;
}

export function auditStatusIcon(status: FranchiseAuditStatus): string {
  if (status === 'PASS') return '✓';
  if (status === 'NEEDS_ATTENTION') return '⚠';
  return '✗';
}

export function formatAuditDate(value: string | null | undefined): string {
  if (!value) return '—';
  const [year, month, day] = value.split('-').map(Number);
  if (!year || !month || !day) return value;
  const parsed = new Date(Date.UTC(year, month - 1, day));
  const monthLabel = parsed.toLocaleDateString('en-GB', { month: 'short', timeZone: 'UTC' });
  return `${String(day).padStart(2, '0')}-${monthLabel}-${year}`;
}

export function formatAuditCreated(value: string | null | undefined): string {
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
