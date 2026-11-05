import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorBanner, Field, LoadingBlock, StatCard, SuccessBanner } from '../../components/ui';
import {
  exportSalesReport,
  fetchDailyRevenue,
  fetchPaymentTotals,
  fetchProductSales,
  fetchReportSummary,
} from '../../lib/reportsApi';
import { formatINR } from '../../types/pos';
import { formatBillDateTime, paymentLabel } from '../../types/orders';
import type { ReportPeriod } from '../../types/reports';
import { apiErrorMessage } from '../franchises/status';
import {
  customRangeValidationError,
  shouldFetchReports,
} from './reportDateRange';
import {
  REPORT_EXPORT_SUCCESS,
  toReportExportError,
} from './reportExport';
import { DailyRevenueChart } from './DailyRevenueChart';

export function ReportsPage() {
  const [period, setPeriod] = useState<ReportPeriod>('7d');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [generating, setGenerating] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  const rangeError = customRangeValidationError(period, customFrom, customTo);
  const canFetch = shouldFetchReports(period, customFrom, customTo);
  const canGenerate = canFetch;

  const rangeKey = period === 'custom' ? [customFrom, customTo] : [];
  const summaryQuery = useQuery({
    queryKey: ['reports-summary', period, ...rangeKey],
    queryFn: () => fetchReportSummary(period, customFrom, customTo),
    enabled: canFetch,
  });
  const dailyQuery = useQuery({
    queryKey: ['reports-daily', period, ...rangeKey],
    queryFn: () => fetchDailyRevenue(period, customFrom, customTo),
    enabled: canFetch,
  });
  const productsQuery = useQuery({
    queryKey: ['reports-products', period, ...rangeKey],
    queryFn: () => fetchProductSales(period, customFrom, customTo),
    enabled: canFetch,
  });
  const paymentsQuery = useQuery({
    queryKey: ['reports-payments', period, ...rangeKey],
    queryFn: () => fetchPaymentTotals(period, customFrom, customTo),
    enabled: canFetch,
  });

  const loading =
    canFetch &&
    (summaryQuery.isLoading || dailyQuery.isLoading || productsQuery.isLoading || paymentsQuery.isLoading);
  const error = canFetch
    ? summaryQuery.error || dailyQuery.error || productsQuery.error || paymentsQuery.error
    : null;
  const summary = canFetch ? summaryQuery.data : undefined;
  const products = productsQuery.data?.items ?? [];
  const payments = paymentsQuery.data?.items ?? [];
  const recentBills = summary?.recent_bills ?? [];

  async function handleGenerate() {
    if (!canGenerate || generating) return;
    setGenerating(true);
    setExportError(null);
    setExportSuccess(null);
    try {
      await exportSalesReport(period, customFrom, customTo);
      setExportSuccess(REPORT_EXPORT_SUCCESS);
    } catch (err) {
      setExportError(await toReportExportError(err));
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="mx-auto max-w-[860px]">
      <div className="mb-3.5 flex items-center justify-between gap-3">
        <div>
          <h1 className="font-serif text-xl font-bold text-[#1A1A18]">Sales Reports</h1>
          <p className="text-xs text-[#8A8A84]">Performance overview</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            aria-label="Report period"
            value={period}
            onChange={(event) => setPeriod(event.target.value as ReportPeriod)}
            className="rounded-[7px] border border-[#E0DDD5] bg-white px-2.5 py-1.5 text-xs outline-none focus:border-[#1A7A4A]"
          >
            <option value="today">Today</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="custom">Custom Date Range</option>
          </select>
          <Button size="sm" onClick={() => void handleGenerate()} disabled={!canGenerate || generating}>
            {generating ? 'Generating...' : 'Generate Report'}
          </Button>
        </div>
      </div>

      {period === 'custom' ? (
        <div className="mb-3.5 grid gap-3 sm:grid-cols-2">
          <Field
            id="report-start-date"
            label="From"
            type="date"
            value={customFrom}
            onChange={(event) => setCustomFrom(event.target.value)}
            aria-label="Start date"
          />
          <Field
            id="report-end-date"
            label="To"
            type="date"
            value={customTo}
            onChange={(event) => setCustomTo(event.target.value)}
            aria-label="End date"
          />
        </div>
      ) : null}

      {rangeError ? (
        <p className="mb-3.5 text-xs text-red-600" role="alert">
          {rangeError}
        </p>
      ) : null}

      {exportSuccess ? (
        <div className="mb-3.5">
          <SuccessBanner message={exportSuccess} />
        </div>
      ) : null}
      {exportError ? (
        <div className="mb-3.5">
          <ErrorBanner message={exportError} />
        </div>
      ) : null}

      {loading ? <LoadingBlock label="Loading reports…" /> : null}
      {error ? <ErrorBanner message={apiErrorMessage(error, 'Unable to load reports.')} /> : null}

      {!loading && !error && summary ? (
        <>
          <div className="mb-3.5 grid grid-cols-2 gap-2.5 md:grid-cols-4">
            <StatCard label="Revenue" value={formatINR(summary.revenue)} color="green" />
            <StatCard label="Orders" value={summary.orders} color="orange" />
            <StatCard label="Avg Order" value={formatINR(summary.avg_order)} color="navy" />
            <StatCard label="Items Sold" value={summary.items_sold} color="mint" />
          </div>

          <div className="mb-3">
            <DailyRevenueChart items={dailyQuery.data?.items ?? []} />
          </div>

          <div className="grid gap-2.5 md:grid-cols-2">
            <div className="rounded-[10px] border border-[#E0DDD5] bg-white p-3.5">
              <div className="mb-2.5 text-[13px] font-semibold text-[#1A1A18]">Top Products</div>
              {products.length === 0 ? (
                <p className="text-xs text-[#8A8A84]">No sales yet</p>
              ) : (
                products.map((product, index) => (
                  <div
                    key={product.product_name}
                    className="flex items-center gap-2 border-b border-[#E0DDD5] py-1.5 last:border-b-0"
                  >
                    <div
                      className={`flex h-[18px] w-[18px] items-center justify-center rounded-full text-[9px] font-bold ${
                        index < 3 ? 'bg-[#1A7A4A] text-white' : 'bg-[#E6F4EC] text-[#8A8A84]'
                      }`}
                    >
                      {index + 1}
                    </div>
                    <div className="flex-1 text-xs text-[#1A1A18]">{product.product_name}</div>
                    <div className="text-[10px] text-[#8A8A84]">{product.quantity}</div>
                    <div className="text-xs font-semibold text-[#1A7A4A]">{formatINR(product.revenue)}</div>
                  </div>
                ))
              )}
            </div>

            <div className="flex flex-col gap-2.5">
              <div className="rounded-[10px] border border-[#E0DDD5] bg-white p-3.5">
                <div className="mb-2 text-[13px] font-semibold text-[#1A1A18]">Payment Methods</div>
                {payments.map((row) => (
                  <div
                    key={row.payment_method}
                    className="flex justify-between border-b border-[#E0DDD5] py-1.5 text-xs last:border-b-0"
                  >
                    <span className="text-[#4A4A46]">{paymentLabel(row.payment_method)}</span>
                    <span className="font-semibold text-[#1A1A18]">{formatINR(row.amount)}</span>
                  </div>
                ))}
              </div>

              <div className="rounded-[10px] border border-[#E0DDD5] bg-white p-3.5">
                <div className="mb-2 text-[13px] font-semibold text-[#1A1A18]">Recent Bills</div>
                {recentBills.length === 0 ? (
                  <p className="text-xs text-[#8A8A84]">No bills yet</p>
                ) : (
                  recentBills.map((bill) => {
                    const when = formatBillDateTime(bill.completed_at);
                    return (
                      <Link
                        key={bill.id}
                        to={`/bills/${bill.id}`}
                        className="flex justify-between border-b border-[#E0DDD5] py-1.5 text-[11px] last:border-b-0 hover:bg-[#FDFAF4]"
                      >
                        <div>
                          <span className="font-semibold text-[#1A1A18]">{bill.bill_number}</span>
                          <span className="ml-1.5 text-[#8A8A84]">{when.time}</span>
                        </div>
                        <span className="font-semibold text-[#1A7A4A]">{formatINR(bill.total_amount)}</span>
                      </Link>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </>
      ) : null}

      {!loading && !error && !summary && !rangeError ? <EmptyState title="No report data" /> : null}
    </div>
  );
}
