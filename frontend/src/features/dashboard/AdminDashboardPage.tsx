import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorBanner, LoadingBlock, StatCard } from '../../components/ui';
import { fetchAdminDashboard } from '../../lib/reportsApi';
import { formatINR } from '../../types/pos';
import { formatLongDate } from '../../types/reports';
import { useAuth } from '../auth/AuthProvider';
import { apiErrorMessage } from '../franchises/status';

export function AdminDashboardPage() {
  const { profile } = useAuth();
  const query = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: fetchAdminDashboard,
  });

  const firstName = profile?.full_name?.split(' ')[0] || 'Admin';
  const data = query.data;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-3.5">
        <h1 className="font-serif text-[22px] font-bold text-[#1A1A18]">Good day, {firstName}</h1>
        <p className="text-xs text-[#8A8A84]">{formatLongDate()}</p>
      </div>

      {query.isLoading ? <LoadingBlock label="Loading dashboard…" /> : null}
      {query.isError ? (
        <ErrorBanner message={apiErrorMessage(query.error, 'Unable to load dashboard.')} />
      ) : null}

      {data ? (
        <>
          <div className="mb-3.5 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            <StatCard
              label="Today's Revenue"
              value={formatINR(data.today_revenue)}
              sub="All outlets"
              color="green"
            />
            <StatCard label="Orders Today" value={data.orders_today} color="orange" />
            <StatCard label="Active Outlets" value={data.active_outlets} color="navy" />
            <StatCard
              label="Top Seller"
              value={data.top_seller_name ?? '—'}
              sub={data.top_seller_name ? `${data.top_seller_quantity} sold` : 'No sales yet'}
              color="mint"
            />
          </div>

          <div className="mb-2.5 overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white">
            <div className="border-b border-[#E0DDD5] px-[15px] py-[11px] text-[13px] font-semibold text-[#1A1A18]">
              Outlet Performance — Today
            </div>
            {data.outlets.length === 0 ? (
              <div className="px-4 py-[18px] text-center text-xs text-[#8A8A84]">No outlets yet.</div>
            ) : (
              data.outlets.map((outlet) => (
                <div
                  key={outlet.franchise_id}
                  className="flex items-center justify-between gap-3 border-b border-[#E0DDD5] px-[15px] py-2.5 last:border-b-0"
                >
                  <div className="text-[13px] font-medium text-[#1A1A18]">{outlet.franchise_name}</div>
                  <div className="text-right">
                    <div className="text-sm font-bold text-[#1A7A4A]">{formatINR(outlet.revenue)}</div>
                    <div className="text-[10px] text-[#8A8A84]">
                      {outlet.orders} order{outlet.orders === 1 ? '' : 's'}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-[10px] border border-[rgba(26,122,74,.2)] bg-[#E6F4EC] px-4 py-3">
            <div>
              <div className="mb-0.5 text-xs font-semibold text-[#1A7A4A]">All-time Revenue</div>
              <div className="font-serif text-2xl font-bold text-[#0D4F2E]">{formatINR(data.all_time_revenue)}</div>
            </div>
            <div className="text-[11px] text-[#2E9E62]">
              From {data.total_bills} total bill{data.total_bills === 1 ? '' : 's'}
            </div>
          </div>
        </>
      ) : null}

      {!query.isLoading && !query.isError && !data ? <EmptyState title="No dashboard data" /> : null}
    </div>
  );
}
