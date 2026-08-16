import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { Badge, Button, EmptyState, ErrorBanner, Field, LoadingBlock, SelectField } from '../../components/ui';
import { useAuth } from '../auth/AuthProvider';
import { listFranchises } from '../../lib/franchisesApi';
import { listAudits } from '../../lib/auditsApi';
import { apiErrorMessage } from '../franchises/status';
import {
  auditStatusLabel,
  auditStatusTone,
  formatAuditCreated,
  formatAuditDate,
  type FranchiseAuditStatus,
} from '../../types/audit';

const PAGE_SIZE = 20;

export function AuditsPage() {
  const { profile } = useAuth();
  const isAdmin = profile?.role === 'SYSTEM_ADMIN';

  const [franchiseFilter, setFranchiseFilter] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [overallStatus, setOverallStatus] = useState<FranchiseAuditStatus | ''>('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [franchiseFilter, fromDate, toDate, overallStatus]);

  const franchisesQuery = useQuery({
    queryKey: ['admin-franchises-options'],
    queryFn: () => listFranchises({ include_archived: true }),
    enabled: isAdmin,
  });

  const listQuery = useQuery({
    queryKey: ['franchise-audits', franchiseFilter, fromDate, toDate, overallStatus, page],
    queryFn: () =>
      listAudits({
        franchise_id: isAdmin && franchiseFilter ? franchiseFilter : undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
        overall_status: overallStatus,
        page,
        page_size: PAGE_SIZE,
      }),
  });

  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const franchises = useMemo(
    () => [...(franchisesQuery.data?.items ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
    [franchisesQuery.data?.items],
  );

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">Franchise Operational Audit</h1>
          <p className="mt-1 text-sm text-[#8A8A84]">
            Completed operational inspections. Historical results are never recalculated.
          </p>
        </div>
        <Link to="/audit/new">
          <Button>Create Audit</Button>
        </Link>
      </div>

      <div className="mb-4 grid gap-3 rounded-xl border border-[#E0DDD5] bg-white p-4 md:grid-cols-2 lg:grid-cols-4">
        {isAdmin ? (
          <SelectField
            label="Franchise"
            value={franchiseFilter}
            onChange={(event) => setFranchiseFilter(event.target.value)}
          >
            <option value="">All Franchises</option>
            {franchises.map((franchise) => (
              <option key={franchise.id} value={franchise.id}>
                {franchise.name}
              </option>
            ))}
          </SelectField>
        ) : null}
        <Field
          label="From Date"
          type="date"
          value={fromDate}
          onChange={(event) => setFromDate(event.target.value)}
        />
        <Field
          label="To Date"
          type="date"
          value={toDate}
          onChange={(event) => setToDate(event.target.value)}
        />
        <SelectField
          label="Overall Status"
          value={overallStatus}
          onChange={(event) => setOverallStatus(event.target.value as FranchiseAuditStatus | '')}
        >
          <option value="">All</option>
          <option value="PASS">PASS</option>
          <option value="NEEDS_ATTENTION">NEEDS ATTENTION</option>
          <option value="FAIL">FAIL</option>
        </SelectField>
      </div>

      {listQuery.isLoading ? <LoadingBlock label="Loading audits…" /> : null}
      {listQuery.isError ? (
        <ErrorBanner message={apiErrorMessage(listQuery.error, 'Unable to load audits.')} />
      ) : null}

      {!listQuery.isLoading && !listQuery.isError && items.length === 0 ? (
        <EmptyState title="No audits" hint="Create an audit or try another filter." />
      ) : null}

      {items.length > 0 ? (
        <>
          <div className="overflow-x-auto rounded-xl border border-[#E0DDD5] bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
                <tr>
                  {isAdmin ? <th className="px-4 py-3 font-semibold">Franchise</th> : null}
                  <th className="px-4 py-3 font-semibold">Audit Date</th>
                  <th className="px-4 py-3 font-semibold">Auditor</th>
                  <th className="px-4 py-3 font-semibold">Overall Result</th>
                  <th className="px-4 py-3 font-semibold">Created</th>
                  <th className="px-4 py-3 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-[#E0DDD5] last:border-b-0">
                    {isAdmin ? <td className="px-4 py-3">{item.franchise_name}</td> : null}
                    <td className="px-4 py-3">{formatAuditDate(item.audit_date)}</td>
                    <td className="px-4 py-3">{item.auditor_name}</td>
                    <td className="px-4 py-3">
                      <Badge tone={auditStatusTone(item.overall_status)}>
                        {auditStatusLabel(item.overall_status)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">{formatAuditCreated(item.created_at)}</td>
                    <td className="px-4 py-3">
                      <Link to={`/audit/${item.id}`}>
                        <Button size="sm" variant="outline">
                          View
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-[#8A8A84]">
            <div>
              Page {page} of {pageCount} · {total} audit{total === 1 ? '' : 's'}
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
