import type { ReactNode } from 'react';

import { Badge, Button, EmptyState, ErrorBanner } from '../../components/ui';
import type { FranchisePayment } from '../../types/franchise';
import { buildPaymentHistory } from './offlinePayment';

export function PaymentHistorySection({
  payments,
  onRecord,
}: {
  payments: FranchisePayment[] | null | undefined;
  onRecord: () => void;
}) {
  const loadFailed = !Array.isArray(payments);
  const history = loadFailed ? null : buildPaymentHistory(payments);

  return (
    <section className="mt-6 rounded-[10px] border border-[#E0DDD5] bg-white px-4 py-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-serif text-xl font-bold text-[#1A1A18]">Payment History</h2>
          <p className="mt-1 text-sm text-[#8A8A84]">
            Offline payments recorded for this franchise.
          </p>
        </div>
        <Button onClick={onRecord}>Record Offline Payment</Button>
      </div>

      {loadFailed ? (
        <ErrorBanner message="Unable to load payment history." />
      ) : null}

      {history && history.rows.length > 0 ? (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-3">
            <SummaryStat label="Total Paid" value={history.totalPaidLabel} />
            <SummaryStat label="Latest Payment Date" value={history.latestDateLabel} />
            <SummaryStat
              label="Latest Payment Status"
              value={
                <Badge tone={history.latestStatusTone}>{history.latestStatusLabel}</Badge>
              }
            />
          </div>
          <div className="overflow-x-auto rounded-xl border border-[#E0DDD5]">
            <table className="min-w-[40rem] w-full text-left text-sm">
              <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
                <tr>
                  <th className="px-4 py-3 font-semibold">Date</th>
                  <th className="px-4 py-3 font-semibold">Amount</th>
                  <th className="px-4 py-3 font-semibold">Payment Method</th>
                  <th className="px-4 py-3 font-semibold">Reference</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Remarks</th>
                </tr>
              </thead>
              <tbody>
                {history.rows.map((row) => (
                  <tr key={row.id} className="border-b border-[#E0DDD5] last:border-b-0">
                    <td className="px-4 py-3 text-[#1A1A18]">{row.dateLabel}</td>
                    <td className="px-4 py-3 font-medium text-[#1A1A18]">{row.amountLabel}</td>
                    <td className="px-4 py-3 text-[#1A1A18]">{row.methodLabel}</td>
                    <td className="px-4 py-3 text-[#1A1A18]">{row.reference}</td>
                    <td className="px-4 py-3">
                      <Badge tone={row.statusTone}>{row.statusLabel}</Badge>
                    </td>
                    <td className="px-4 py-3 text-[#1A1A18]">{row.remarks}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {history && history.rows.length === 0 ? (
        <EmptyState title="No payments recorded yet." hint="Record an offline payment to add the first entry." />
      ) : null}
    </section>
  );
}

function SummaryStat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-xl border border-[#E0DDD5] bg-[#FDFAF4] px-4 py-3">
      <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">{label}</div>
      <div className="mt-1 text-sm font-semibold text-[#1A1A18]">{value}</div>
    </div>
  );
}
