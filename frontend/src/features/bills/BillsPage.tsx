import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { ActionButton, ActionsTd, ActionsTh, Badge, Button, EmptyState, ErrorBanner, Field, LoadingBlock, SelectField } from '../../components/ui';
import { useAuth } from '../auth/AuthProvider';
import { listFranchises } from '../../lib/franchisesApi';
import { fetchCompletedOrders } from '../../lib/ordersApi';
import { apiErrorMessage } from '../franchises/status';
import { formatINR } from '../../types/pos';
import {
  datePresetRange,
  formatBillDateTime,
  paymentLabel,
  type DatePreset,
} from '../../types/orders';
import type { PosPaymentMethod } from '../../types/pos';

const PAGE_SIZE = 20;

export function BillsPage() {
  const { profile } = useAuth();
  const isAdmin = profile?.role === 'SYSTEM_ADMIN';

  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [preset, setPreset] = useState<DatePreset>('today');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [payment, setPayment] = useState<PosPaymentMethod | ''>('');
  const [franchiseFilter, setFranchiseFilter] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => window.clearTimeout(handle);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, preset, customFrom, customTo, payment, franchiseFilter]);

  const range = datePresetRange(preset, customFrom, customTo);
  const adminReady = !isAdmin || Boolean(franchiseFilter);
  const franchiseId = isAdmin
    ? franchiseFilter === 'all'
      ? undefined
      : franchiseFilter || undefined
    : undefined;

  const franchisesQuery = useQuery({
    queryKey: ['admin-franchises-options'],
    queryFn: () => listFranchises({ include_archived: true }),
    enabled: isAdmin,
  });

  const listQuery = useQuery({
    queryKey: [
      'completed-bills',
      debouncedSearch,
      preset,
      range.from_date,
      range.to_date,
      payment,
      franchiseId ?? franchiseFilter,
      page,
    ],
    queryFn: () =>
      fetchCompletedOrders({
        bill_number: debouncedSearch || undefined,
        payment_method: payment,
        from_date: range.from_date,
        to_date: range.to_date,
        franchise_id: franchiseId,
        page,
        page_size: PAGE_SIZE,
      }),
    enabled: adminReady,
  });

  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const showFranchiseColumn = isAdmin;
  const franchises = useMemo(
    () => [...(franchisesQuery.data?.items ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
    [franchisesQuery.data?.items],
  );

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-5">
        <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">Bills / Order History</h1>
        <p className="mt-1 text-sm text-[#8A8A84]">Completed bills only. Historical totals are never recalculated.</p>
      </div>

      <div className="mb-4 grid gap-3 rounded-xl border border-[#E0DDD5] bg-white p-4 md:grid-cols-2 lg:grid-cols-4">
        <Field
          label="Search Bill Number"
          placeholder="RS-0001"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <SelectField
          label="Date"
          value={preset}
          onChange={(event) => setPreset(event.target.value as DatePreset)}
        >
          <option value="today">Today</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
          <option value="custom">Custom range</option>
        </SelectField>
        <SelectField
          label="Payment"
          value={payment}
          onChange={(event) => setPayment(event.target.value as PosPaymentMethod | '')}
        >
          <option value="">All</option>
          <option value="CASH">Cash</option>
          <option value="UPI">UPI</option>
          <option value="CARD">Card</option>
        </SelectField>
        {isAdmin ? (
          <SelectField
            label="Franchise"
            value={franchiseFilter}
            onChange={(event) => setFranchiseFilter(event.target.value)}
          >
            <option value="">Select franchise</option>
            <option value="all">All Franchises</option>
            {franchises.map((franchise) => (
              <option key={franchise.id} value={franchise.id}>
                {franchise.name}
              </option>
            ))}
          </SelectField>
        ) : (
          <div />
        )}
        {preset === 'custom' ? (
          <>
            <Field
              label="From"
              type="date"
              value={customFrom}
              onChange={(event) => setCustomFrom(event.target.value)}
            />
            <Field
              label="To"
              type="date"
              value={customTo}
              onChange={(event) => setCustomTo(event.target.value)}
            />
          </>
        ) : null}
      </div>

      {!adminReady ? (
        <EmptyState title="Select a franchise" hint="Choose a franchise to view completed bills." />
      ) : null}

      {adminReady && listQuery.isLoading ? <LoadingBlock label="Loading bills…" /> : null}
      {adminReady && listQuery.isError ? (
        <ErrorBanner message={apiErrorMessage(listQuery.error, 'Unable to load bills.')} />
      ) : null}

      {adminReady && !listQuery.isLoading && !listQuery.isError && items.length === 0 ? (
        <EmptyState title="No completed bills" hint="Try another date range, payment method, or bill number." />
      ) : null}

      {adminReady && items.length > 0 ? (
        <>
          <div className="overflow-x-auto rounded-xl border border-[#E0DDD5] bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
                <tr>
                  <th className="px-4 py-3 font-semibold">Bill No</th>
                  <th className="px-4 py-3 font-semibold">Date / Time</th>
                  {showFranchiseColumn ? <th className="px-4 py-3 font-semibold">Franchise</th> : null}
                  <th className="px-4 py-3 font-semibold">Cashier</th>
                  <th className="px-4 py-3 font-semibold">Payment</th>
                  <th className="px-4 py-3 font-semibold">Total</th>
                  <ActionsTh>Action</ActionsTh>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const when = formatBillDateTime(item.completed_at || item.created_at);
                  return (
                    <tr key={item.id} className="border-b border-[#E0DDD5] last:border-b-0">
                      <td className="px-4 py-3 font-semibold">{item.bill_number}</td>
                      <td className="px-4 py-3">
                        {when.date} {when.time}
                      </td>
                      {showFranchiseColumn ? (
                        <td className="px-4 py-3">{item.franchise_name ?? '—'}</td>
                      ) : null}
                      <td className="px-4 py-3">{item.cashier_name ?? '—'}</td>
                      <td className="px-4 py-3">
                        <Badge tone="navy">{paymentLabel(item.payment_method)}</Badge>
                      </td>
                      <td className="px-4 py-3 font-semibold">{formatINR(item.total_amount)}</td>
                      <ActionsTd>
                        <Link to={`/bills/${item.id}`}>
                          <ActionButton variant="outline">View</ActionButton>
                        </Link>
                      </ActionsTd>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-[#8A8A84]">
            <div>
              Page {page} of {pageCount} · {total} bill{total === 1 ? '' : 's'}
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="muted" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
                Previous
              </Button>
              <Button
                size="sm"
                variant="muted"
                disabled={page >= pageCount}
                onClick={() => setPage((value) => value + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
