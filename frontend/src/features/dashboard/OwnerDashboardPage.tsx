import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorBanner, LoadingBlock, StatCard } from '../../components/ui';
import { fetchOwnerDashboard } from '../../lib/reportsApi';
import { formatINR } from '../../types/pos';
import { formatBillDateTime } from '../../types/orders';
import { apiErrorMessage } from '../franchises/status';

export function OwnerDashboardPage() {
  const query = useQuery({
    queryKey: ['owner-dashboard'],
    queryFn: fetchOwnerDashboard,
  });
  const data = query.data;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-3.5">
        <h1 className="font-serif text-xl font-bold text-[#1A1A18]">Outlet Dashboard</h1>
        <p className="text-xs text-[#8A8A84]">{data?.franchise_name || 'My Outlet'}</p>
      </div>

      {query.isLoading ? <LoadingBlock label="Loading dashboard…" /> : null}
      {query.isError ? (
        <ErrorBanner message={apiErrorMessage(query.error, 'Unable to load dashboard.')} />
      ) : null}

      {data ? (
        <>
          <div className="mb-3.5 grid grid-cols-2 gap-2.5 md:grid-cols-4">
            <StatCard label="Today's Revenue" value={formatINR(data.today_revenue)} color="green" />
            <StatCard label="Bills Today" value={data.bills_today} color="orange" />
            <StatCard label="Top Product" value={data.top_product_name ?? '—'} color="mint" />
            <StatCard label="All-time" value={formatINR(data.all_time_revenue)} color="navy" />
          </div>

          <div className="overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white">
            <div className="border-b border-[#E0DDD5] px-3.5 py-2.5 text-xs font-semibold text-[#1A1A18]">
              Recent Bills
            </div>
            {data.recent_bills.length === 0 ? (
              <div className="px-4 py-[18px] text-center text-xs text-[#8A8A84]">
                No bills today yet — start billing!
              </div>
            ) : (
              data.recent_bills.map((bill) => {
                const when = formatBillDateTime(bill.completed_at);
                return (
                  <Link
                    key={bill.id}
                    to={`/bills/${bill.id}`}
                    className="flex items-center justify-between border-b border-[#E0DDD5] px-3.5 py-2 text-xs last:border-b-0 hover:bg-[#FDFAF4]"
                  >
                    <div>
                      <span className="font-semibold text-[#1A1A18]">{bill.bill_number}</span>
                      <span className="ml-1.5 text-[#8A8A84]">{when.time}</span>
                    </div>
                    <span className="font-bold text-[#1A7A4A]">{formatINR(bill.total_amount)}</span>
                  </Link>
                );
              })
            )}
          </div>
        </>
      ) : null}

      {!query.isLoading && !query.isError && !data ? <EmptyState title="No dashboard data" /> : null}
    </div>
  );
}
