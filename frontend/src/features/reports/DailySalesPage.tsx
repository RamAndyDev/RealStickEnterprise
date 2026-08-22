import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { ActionButton, ActionsTd, ActionsTh, Badge, EmptyState, ErrorBanner, Field, LoadingBlock, StatCard } from '../../components/ui';
import { fetchEmployeeDailySales } from '../../lib/reportsApi';
import { formatINR } from '../../types/pos';
import { formatBillDateTime, paymentLabel } from '../../types/orders';
import { apiErrorMessage } from '../franchises/status';

function utcTodayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatSalesDate(value: string): string {
  const [year, month, day] = value.split('-').map(Number);
  if (!year || !month || !day) return value;
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

export function DailySalesPage() {
  const today = utcTodayIso();
  const [selectedDate, setSelectedDate] = useState(today);
  const query = useQuery({
    queryKey: ['employee-daily-sales', selectedDate],
    queryFn: () => fetchEmployeeDailySales(selectedDate),
  });
  const data = query.data;
  const bills = data?.bills ?? [];
  const displayDate = data?.date ?? selectedDate;

  function onDateChange(value: string) {
    if (!value) return;
    setSelectedDate(value > today ? today : value);
  }

  return (
    <div className="mx-auto max-w-[860px]">
      <div className="mb-3.5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-xl font-bold text-[#1A1A18]">Daily Sales</h1>
          <p className="text-xs text-[#8A8A84]">{formatSalesDate(displayDate)}</p>
        </div>
        <div className="w-full max-w-[220px]">
          <Field
            label="Date"
            type="date"
            value={selectedDate}
            max={today}
            onChange={(event) => onDateChange(event.target.value)}
          />
        </div>
      </div>

      {query.isLoading ? <LoadingBlock label="Loading daily sales…" /> : null}
      {query.isError ? (
        <ErrorBanner message={apiErrorMessage(query.error, 'Unable to load daily sales.')} />
      ) : null}

      {data ? (
        <>
          <div className="mb-3.5 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            <StatCard label="Revenue" value={formatINR(data.summary.revenue)} color="green" />
            <StatCard label="Bills" value={data.summary.bills} color="orange" />
            <StatCard label="Items Sold" value={data.summary.items_sold} color="mint" />
            <StatCard label="Average Bill" value={formatINR(data.summary.average_bill)} color="navy" />
          </div>

          <div className="mb-3.5 rounded-[10px] border border-[#E0DDD5] bg-white p-3.5">
            <div className="mb-2 text-[13px] font-semibold text-[#1A1A18]">Payment Summary</div>
            <div className="flex justify-between border-b border-[#E0DDD5] py-1.5 text-xs">
              <span className="text-[#4A4A46]">{paymentLabel('CASH')}</span>
              <span className="font-semibold text-[#1A1A18]">{formatINR(data.payments.cash)}</span>
            </div>
            <div className="flex justify-between border-b border-[#E0DDD5] py-1.5 text-xs">
              <span className="text-[#4A4A46]">{paymentLabel('UPI')}</span>
              <span className="font-semibold text-[#1A1A18]">{formatINR(data.payments.upi)}</span>
            </div>
            <div className="flex justify-between py-1.5 text-xs">
              <span className="text-[#4A4A46]">{paymentLabel('CARD')}</span>
              <span className="font-semibold text-[#1A1A18]">{formatINR(data.payments.card)}</span>
            </div>
          </div>

          <div className="overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white">
            <div className="border-b border-[#E0DDD5] px-3.5 py-2.5 text-[13px] font-semibold text-[#1A1A18]">
              Bills
            </div>
            {bills.length === 0 ? (
              <div className="p-4">
                <EmptyState title="No sales on this date" />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Bill</th>
                      <th className="px-4 py-3 font-semibold">Time</th>
                      <th className="px-4 py-3 font-semibold">Payment</th>
                      <th className="px-4 py-3 font-semibold">Amount</th>
                      <ActionsTh>Action</ActionsTh>
                    </tr>
                  </thead>
                  <tbody>
                    {bills.map((bill) => {
                      const when = formatBillDateTime(bill.completed_at);
                      return (
                        <tr key={bill.id} className="border-b border-[#E0DDD5] last:border-b-0">
                          <td className="px-4 py-3 font-semibold">{bill.bill_number}</td>
                          <td className="px-4 py-3">{when.time}</td>
                          <td className="px-4 py-3">
                            <Badge tone="navy">{paymentLabel(bill.payment_method)}</Badge>
                          </td>
                          <td className="px-4 py-3 font-semibold">{formatINR(bill.total_amount)}</td>
                          <ActionsTd>
                            <Link to={`/bills/${bill.id}`}>
                              <ActionButton variant="outline">View</ActionButton>
                            </Link>
                            <a href={`/print/receipt/${bill.id}?from=daily-sales`} target="_blank" rel="noreferrer">
                              <ActionButton variant="muted">Print</ActionButton>
                            </a>
                          </ActionsTd>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
