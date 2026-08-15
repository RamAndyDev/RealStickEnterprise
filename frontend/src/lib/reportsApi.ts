import { api } from './api';
import type {
  AdminDashboard,
  DailyRevenueResponse,
  EmployeeDailySales,
  OwnerDashboard,
  PaymentTotalsResponse,
  ProductSalesResponse,
  ReportPeriod,
  ReportSummary,
} from '../types/reports';

export async function fetchReportSummary(period: ReportPeriod): Promise<ReportSummary> {
  const { data } = await api.get<ReportSummary>('/reports/summary', { params: { period } });
  return data;
}

export async function fetchDailyRevenue(period: ReportPeriod): Promise<DailyRevenueResponse> {
  const { data } = await api.get<DailyRevenueResponse>('/reports/daily', { params: { period } });
  return data;
}

export async function fetchProductSales(period: ReportPeriod): Promise<ProductSalesResponse> {
  const { data } = await api.get<ProductSalesResponse>('/reports/products', { params: { period } });
  return data;
}

export async function fetchPaymentTotals(period: ReportPeriod): Promise<PaymentTotalsResponse> {
  const { data } = await api.get<PaymentTotalsResponse>('/reports/payments', { params: { period } });
  return data;
}

export async function fetchAdminDashboard(): Promise<AdminDashboard> {
  const { data } = await api.get<AdminDashboard>('/reports/dashboard/admin');
  return data;
}

export async function fetchOwnerDashboard(): Promise<OwnerDashboard> {
  const { data } = await api.get<OwnerDashboard>('/reports/dashboard/owner');
  return data;
}

export async function fetchEmployeeDailySales(date?: string): Promise<EmployeeDailySales> {
  const { data } = await api.get<EmployeeDailySales>('/reports/employee/daily', {
    params: date ? { date } : undefined,
  });
  return data;
}
