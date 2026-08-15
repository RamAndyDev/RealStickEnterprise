export type PosPaymentMethod = 'CASH' | 'UPI' | 'CARD';

export type PosMenuCategory = {
  id: string;
  name: string;
  display_order: number;
};

export type PosMenuItem = {
  product_id: string;
  name: string;
  description: string | null;
  image_url: string | null;
  category_id: string | null;
  category_name: string | null;
  selling_price: number;
  available_for_pos: boolean;
};

export type PosMenuResponse = {
  franchise_id: string;
  franchise_name: string | null;
  gst_rate: number | null;
  cgst_rate: number | null;
  sgst_rate: number | null;
  categories: PosMenuCategory[];
  items: PosMenuItem[];
};

export type PosOffer = {
  id: string;
  name: string;
  description: string | null;
  discount_type: string;
  discount_value: number;
  valid_from: string | null;
  valid_to: string | null;
};

export type PosOfferListResponse = {
  items: PosOffer[];
  total: number;
};

export type PosCartLine = {
  product_id: string;
  name: string;
  image_url: string | null;
  selling_price: number;
  quantity: number;
};

export type PosOrderItem = {
  id?: string | null;
  product_id: string;
  product_name_snapshot: string;
  unit_price: number;
  quantity: number;
  line_discount_amount: number;
  line_total: number;
};

export type PosOrder = {
  id: string;
  franchise_id: string;
  bill_number: string;
  status: string;
  customer_phone: string | null;
  subtotal: number;
  discount_amount: number;
  discount_percent?: number | null;
  discount_value?: number | null;
  discount_type?: string | null;
  offer_id?: string | null;
  offer_name?: string | null;
  taxable_amount: number;
  gst_rate: number;
  gst_amount: number;
  cgst_rate: number;
  sgst_rate: number;
  cgst_amount: number;
  sgst_amount: number;
  total_amount: number;
  payment_method: PosPaymentMethod | string | null;
  cashier_id: string | null;
  cashier_name: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at?: string | null;
  franchise_name: string | null;
  franchise_address: string | null;
  franchise_city: string | null;
  franchise_state: string | null;
  items: PosOrderItem[];
  payment_status: string | null;
};

export type PosOrderCreatePayload = {
  items: { product_id: string; quantity: number }[];
  payment_method: PosPaymentMethod;
  customer_phone?: string | null;
  offer_id?: string | null;
};

export function money(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

export function formatINR(amount: number | null | undefined): string {
  if (amount == null || Number.isNaN(amount)) return '—';
  return `₹${Number(amount).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function previewTotals(
  lines: PosCartLine[],
  discountPercent: number,
  gstRate: number | null,
): {
  subtotal: number;
  discount: number;
  taxable: number;
  cgstRate: number;
  sgstRate: number;
  cgst: number;
  sgst: number;
  gst: number;
  total: number;
} {
  const subtotal = money(lines.reduce((sum, line) => sum + line.selling_price * line.quantity, 0));
  const pct = Math.min(100, Math.max(0, discountPercent || 0));
  const discount = money((subtotal * pct) / 100);
  const taxable = money(Math.max(0, subtotal - discount));
  const cgstRate = gstRate == null ? 0 : money(gstRate / 2);
  const sgstRate = gstRate == null ? 0 : money(gstRate / 2);
  const cgst = gstRate == null ? 0 : money((taxable * cgstRate) / 100);
  const sgst = gstRate == null ? 0 : money((taxable * sgstRate) / 100);
  const gst = money(cgst + sgst);
  return { subtotal, discount, taxable, cgstRate, sgstRate, cgst, sgst, gst, total: money(taxable + gst) };
}
