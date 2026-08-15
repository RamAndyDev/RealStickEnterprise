import type { PosOrder, PosPaymentMethod } from './pos';

export type BillListItem = {
  id: string;
  bill_number: string;
  franchise_id: string;
  franchise_name: string | null;
  cashier_id: string | null;
  cashier_name: string | null;
  created_at: string;
  completed_at: string | null;
  total_amount: number;
  payment_method: PosPaymentMethod | string | null;
};

export type BillListResponse = {
  items: BillListItem[];
  page: number;
  page_size: number;
  total: number;
};

export type BillListParams = {
  franchise_id?: string;
  bill_number?: string;
  payment_method?: PosPaymentMethod | '';
  from_date?: string;
  to_date?: string;
  page?: number;
  page_size?: number;
};

export type CompletedBill = PosOrder;

export type DatePreset = 'today' | '7d' | '30d' | 'custom';

export function toYmd(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function datePresetRange(
  preset: DatePreset,
  customFrom?: string,
  customTo?: string,
): { from_date?: string; to_date?: string } {
  const today = new Date();
  const to = toYmd(today);
  if (preset === 'today') {
    return { from_date: to, to_date: to };
  }
  if (preset === '7d') {
    const from = new Date(today);
    from.setDate(from.getDate() - 6);
    return { from_date: toYmd(from), to_date: to };
  }
  if (preset === '30d') {
    const from = new Date(today);
    from.setDate(from.getDate() - 29);
    return { from_date: toYmd(from), to_date: to };
  }
  return {
    from_date: customFrom || undefined,
    to_date: customTo || undefined,
  };
}

export function paymentLabel(method: string | null | undefined): string {
  if (!method) return '—';
  if (method === 'CASH') return 'Cash';
  if (method === 'UPI') return 'UPI';
  if (method === 'CARD') return 'Card';
  return method;
}

export function formatBillDateTime(value: string | null | undefined): { date: string; time: string } {
  if (!value) return { date: '—', time: '—' };
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return { date: value, time: '—' };
  return {
    date: parsed.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }),
    time: parsed.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
  };
}
