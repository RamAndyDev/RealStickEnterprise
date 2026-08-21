import { api } from './api';
import { reportRequestParams } from '../features/reports/reportDateRange';
import {
  filenameFromContentDisposition,
  salesReportDownloadName,
  triggerBrowserDownload,
} from '../features/reports/reportExport';
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

export async function fetchReportSummary(
  period: ReportPeriod,
  startDate = '',
  endDate = '',
): Promise<ReportSummary> {
  const { data } = await api.get<ReportSummary>('/reports/summary', {
    params: reportRequestParams(period, startDate, endDate),
  });
  return data;
}

export async function fetchDailyRevenue(
  period: ReportPeriod,
  startDate = '',
  endDate = '',
): Promise<DailyRevenueResponse> {
  const { data } = await api.get<DailyRevenueResponse>('/reports/daily', {
    params: reportRequestParams(period, startDate, endDate),
  });
  return data;
}

export async function fetchProductSales(
  period: ReportPeriod,
  startDate = '',
  endDate = '',
): Promise<ProductSalesResponse> {
  const { data } = await api.get<ProductSalesResponse>('/reports/products', {
    params: reportRequestParams(period, startDate, endDate),
  });
  return data;
}

export async function fetchPaymentTotals(
  period: ReportPeriod,
  startDate = '',
  endDate = '',
): Promise<PaymentTotalsResponse> {
  const { data } = await api.get<PaymentTotalsResponse>('/reports/payments', {
    params: reportRequestParams(period, startDate, endDate),
  });
  return data;
}

export async function exportSalesReport(
  period: ReportPeriod,
  startDate = '',
  endDate = '',
): Promise<void> {
  const response = await api.get<Blob>('/reports/export', {
    params: reportRequestParams(period, startDate, endDate),
    responseType: 'blob',
  });
  const filename =
    filenameFromContentDisposition(response.headers['content-disposition']) ??
    salesReportDownloadName(period, startDate, endDate);
  triggerBrowserDownload(response.data, filename);
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
