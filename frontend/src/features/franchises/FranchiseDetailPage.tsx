import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import {
  Badge,
  Button,
  ErrorBanner,
  LoadingBlock,
  SuccessBanner,
} from '../../components/ui';
import { getFranchise } from '../../lib/franchisesApi';
import type { FranchiseDetail } from '../../types/franchise';
import { FranchiseProductsPanel } from '../products/FranchiseProductsPanel';
import { LaunchProgressTrack } from './LaunchProgress';
import { PaymentHistorySection } from './PaymentHistorySection';
import { RecordOfflinePaymentDialog } from './RecordOfflinePaymentDialog';
import { deriveLaunchProgress } from './launchStages';
import { apiErrorMessage, formatDate, statusLabel, statusTone } from './status';

export function FranchiseDetailPage() {
  const { franchiseId } = useParams<{ franchiseId: string }>();
  const queryClient = useQueryClient();
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const detailQuery = useQuery({
    queryKey: ['admin-franchise', franchiseId],
    queryFn: () => getFranchise(franchiseId!),
    enabled: Boolean(franchiseId),
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
  const launchProgress = deriveLaunchProgress({
    status: franchise.status,
    payment_status: franchise.payment_status,
  });

  async function handlePaymentSaved(updated: FranchiseDetail) {
    setFeedback('Offline payment recorded successfully.');
    queryClient.setQueryData(['admin-franchise', franchiseId], updated);
    await queryClient.invalidateQueries({ queryKey: ['admin-franchises'] });
    await queryClient.invalidateQueries({ queryKey: ['admin-franchise', franchiseId] });
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4">
        <Link to="/franchises" className="text-sm text-[#1A7A4A] hover:underline">
          ← Franchise Outlets
        </Link>
      </div>

      {feedback ? (
        <div className="mb-4">
          <SuccessBanner message={feedback} />
        </div>
      ) : null}

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
          <Info label="Launch Stage" value={launchProgress.currentLabel} />
          <Info label="Employee Limit" value={String(franchise.employee_limit)} />
        </div>
      </div>

      <section className="mt-6">
        <LaunchProgressTrack
          source={{
            status: franchise.status,
            payment_status: franchise.payment_status,
          }}
        />
      </section>

      <PaymentHistorySection
        payments={franchise.payments}
        onRecord={() => setPaymentOpen(true)}
      />

      <section className="mt-6 mb-8">
        <FranchiseProductsPanel franchiseId={franchise.id} franchiseName={franchise.name} />
      </section>

      <div className="mb-10">
        <Button variant="outline" onClick={() => window.history.back()}>
          Back
        </Button>
      </div>

      {paymentOpen ? (
        <RecordOfflinePaymentDialog
          franchiseId={franchise.id}
          paymentStatus={franchise.payment_status}
          onClose={() => setPaymentOpen(false)}
          onSaved={handlePaymentSaved}
        />
      ) : null}
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
