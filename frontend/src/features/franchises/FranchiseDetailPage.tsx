import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import {
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  LoadingBlock,
  SuccessBanner,
} from '../../components/ui';
import { getFranchise, updateLaunchChecklistItem } from '../../lib/franchisesApi';
import { FranchiseProductsPanel } from '../products/FranchiseProductsPanel';
import { apiErrorMessage, formatDate, statusLabel, statusTone } from './status';

export function FranchiseDetailPage() {
  const { franchiseId } = useParams<{ franchiseId: string }>();
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const detailQuery = useQuery({
    queryKey: ['admin-franchise', franchiseId],
    queryFn: () => getFranchise(franchiseId!),
    enabled: Boolean(franchiseId),
  });

  const checklistMutation = useMutation({
    mutationFn: ({ itemId, is_completed }: { itemId: string; is_completed: boolean }) =>
      updateLaunchChecklistItem(franchiseId!, itemId, is_completed),
    onSuccess: async () => {
      setFeedback('Launch checklist updated.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-franchise', franchiseId] });
      await queryClient.invalidateQueries({ queryKey: ['admin-franchises'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update checklist item.')),
  });

  if (!franchiseId) {
    return <ErrorBanner message="Missing franchise id." />;
  }

  if (detailQuery.isLoading) {
    return <LoadingBlock label="Loading outlet details…" />;
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <ErrorBanner message={apiErrorMessage(detailQuery.error, 'Unable to load outlet details.')} />
    );
  }

  const franchise = detailQuery.data;
  const headerBg = franchise.status === 'ACTIVE' ? '#0D4F2E' : '#8A8A84';

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4">
        <Link to="/franchises" className="text-sm text-[#1A7A4A] hover:underline">
          ← Franchise Outlets
        </Link>
      </div>

      <div className="overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white">
        <div className="px-5 py-4" style={{ background: headerBg }}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="font-serif text-2xl font-bold text-white">{franchise.name}</h1>
              <p className="mt-1 text-sm text-white/60">
                {[franchise.city, franchise.tier ? `${franchise.tier} Partner` : null]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
            </div>
            <Badge tone={statusTone(franchise.status)}>{statusLabel(franchise.status)}</Badge>
          </div>
        </div>

        <div className="grid gap-4 p-5 sm:grid-cols-2">
          <Info label="Address" value={franchise.address} />
          <Info label="State" value={franchise.state} />
          <Info label="Postal Code" value={franchise.postal_code} />
          <Info label="Outlet Code" value={franchise.code} />
          <Info label="Owner Email" value={franchise.owner_email} />
          <Info
            label="Assigned Owner"
            value={
              franchise.owner
                ? `${franchise.owner.full_name}${franchise.owner.is_active ? '' : ' (inactive)'}`
                : 'Unassigned'
            }
          />
          <Info label="Open Date" value={formatDate(franchise.open_date)} />
          <Info label="Payment Status" value={franchise.payment_status} />
          <Info
            label="Launch Progress"
            value={
              franchise.launch_progress_total
                ? `${franchise.launch_progress_completed}/${franchise.launch_progress_total}`
                : 'No checklist'
            }
          />
          <Info label="Employee Limit" value={String(franchise.employee_limit)} />
        </div>
      </div>

      {feedback ? (
        <div className="mt-4">
          <SuccessBanner message={feedback} />
        </div>
      ) : null}
      {error ? (
        <div className="mt-4">
          <ErrorBanner message={error} />
        </div>
      ) : null}

      <section className="mt-6">
        <h2 className="mb-3 font-serif text-xl font-bold text-[#1A1A18]">Launch Progress</h2>
        {franchise.launch_checklist.length === 0 ? (
          <EmptyState title="No launch checklist items" hint="Checklist seeds when an outlet is created." />
        ) : (
          <div className="space-y-2 rounded-xl border border-[#E0DDD5] bg-white p-4">
            {franchise.launch_checklist.map((item) => (
              <label
                key={item.id}
                className="flex items-start gap-3 rounded-lg border border-[#E0DDD5] px-3 py-2.5"
              >
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={item.is_completed}
                  disabled={checklistMutation.isPending}
                  onChange={(e) =>
                    checklistMutation.mutate({
                      itemId: item.id,
                      is_completed: e.target.checked,
                    })
                  }
                />
                <span>
                  <span className="block text-sm font-medium text-[#1A1A18]">{item.item_name}</span>
                  <span className="text-xs text-[#8A8A84]">
                    {item.is_completed
                      ? `Completed ${formatDate(item.completed_at)}`
                      : 'Pending'}
                  </span>
                </span>
              </label>
            ))}
          </div>
        )}
      </section>

      <section className="mt-6">
        <h2 className="mb-3 font-serif text-xl font-bold text-[#1A1A18]">Franchise Application</h2>
        {franchise.applications.length === 0 ? (
          <EmptyState title="No linked application" hint="Converted applications appear here." />
        ) : (
          <div className="space-y-3">
            {franchise.applications.map((app) => (
              <div key={app.id} className="rounded-xl border border-[#E0DDD5] bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold text-[#1A1A18]">{app.applicant_name}</div>
                  <Badge tone="navy">{app.status}</Badge>
                </div>
                <div className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
                  <Info label="Email" value={app.email} />
                  <Info label="Phone" value={app.phone} />
                  <Info label="City" value={app.city} />
                  <Info label="Investment" value={app.investment_range} />
                </div>
                {app.message ? (
                  <p className="mt-2 text-sm text-[#4A4A46]">{app.message}</p>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="mt-6 mb-8">
        <h2 className="mb-3 font-serif text-xl font-bold text-[#1A1A18]">Payment Status</h2>
        {franchise.payments.length === 0 ? (
          <EmptyState title="No payments recorded" />
        ) : (
          <div className="overflow-x-auto rounded-xl border border-[#E0DDD5] bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
                <tr>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Method</th>
                  <th className="px-4 py-3">Reference</th>
                  <th className="px-4 py-3">Paid</th>
                </tr>
              </thead>
              <tbody>
                {franchise.payments.map((payment) => (
                  <tr key={payment.id} className="border-b border-[#E0DDD5] last:border-b-0">
                    <td className="px-4 py-3">
                      {payment.currency} {Number(payment.amount).toLocaleString('en-IN')}
                    </td>
                    <td className="px-4 py-3">{payment.status}</td>
                    <td className="px-4 py-3">{payment.payment_method ?? '—'}</td>
                    <td className="px-4 py-3">{payment.reference_number ?? '—'}</td>
                    <td className="px-4 py-3">{formatDate(payment.paid_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mb-8">
        <FranchiseProductsPanel franchiseId={franchise.id} franchiseName={franchise.name} />
      </section>

      <div className="mb-10">
        <Button variant="outline" onClick={() => window.history.back()}>
          Back
        </Button>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">{label}</div>
      <div className="mt-1 text-sm text-[#1A1A18]">{value || '—'}</div>
    </div>
  );
}
