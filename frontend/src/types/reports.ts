import type { DatePreset } from './orders';

export type ReportPeriod = Exclude<DatePreset, 'custom'>;

export type ReportBillPreview = {
  id: string;
  bill_number: string;
  completed_at: string | null;
  total_amount: number;
  payment_method: string | null;
};

export type ReportSummary = {
  revenue: number;
  orders: number;
  avg_order: number;
  items_sold: number;
  recent_bills: ReportBillPreview[];
};

export type DailyRevenuePoint = {
  date: string;
  revenue: number;
};

export type DailyRevenueResponse = {
  items: DailyRevenuePoint[];
};

export type ProductSalesRow = {
  product_name: string;
  quantity: number;
  revenue: number;
};

export type ProductSalesResponse = {
  items: ProductSalesRow[];
};

export type PaymentTotalsRow = {
  payment_method: string;
  amount: number;
};

export type PaymentTotalsResponse = {
  items: PaymentTotalsRow[];
};

export type AdminOutletPerformance = {
  franchise_id: string;
  franchise_name: string;
  revenue: number;
  orders: number;
};

export type AdminDashboard = {
  today_revenue: number;
  orders_today: number;
  active_outlets: number;
  top_seller_name: string | null;
  top_seller_quantity: number;
  outlets: AdminOutletPerformance[];
  all_time_revenue: number;
  total_bills: number;
};

export type OwnerDashboard = {
  franchise_id: string;
  franchise_name: string | null;
  today_revenue: number;
  bills_today: number;
  top_product_name: string | null;
  top_product_quantity: number;
  all_time_revenue: number;
  recent_bills: ReportBillPreview[];
};

export type EmployeeDailySalesSummary = {
  revenue: number;
  bills: number;
  items_sold: number;
  average_bill: number;
};

export type EmployeeDailySalesPayments = {
  cash: number;
  upi: number;
  card: number;
};

export type EmployeeDailySales = {
  date: string;
  summary: EmployeeDailySalesSummary;
  payments: EmployeeDailySalesPayments;
  bills: ReportBillPreview[];
};

export function formatChartDate(value: string): string {
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
}

export function formatLongDate(value: Date = new Date()): string {
  return value.toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}
