import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { Badge, Button, ErrorBanner, LoadingBlock } from '../../components/ui';
import { getAudit } from '../../lib/auditsApi';
import { apiErrorMessage } from '../franchises/status';
import {
  auditStatusIcon,
  auditStatusLabel,
  auditStatusTone,
  formatAuditCreated,
  formatAuditDate,
} from '../../types/audit';

export function AuditDetailPage() {
  const { auditId } = useParams();

  const detailQuery = useQuery({
    queryKey: ['franchise-audit', auditId],
    queryFn: () => getAudit(auditId!),
    enabled: Boolean(auditId),
  });

  if (!auditId) {
    return <ErrorBanner message="Missing audit id." />;
  }
  if (detailQuery.isLoading) {
    return <LoadingBlock label="Loading audit…" />;
  }
  if (detailQuery.isError || !detailQuery.data) {
    return (
      <div className="mx-auto max-w-3xl">
        <ErrorBanner message={apiErrorMessage(detailQuery.error, 'Unable to load audit.')} />
        <Link to="/audit" className="mt-4 inline-block text-sm text-[#1A7A4A]">
          ← Back to Audits
        </Link>
      </div>
    );
  }

  const audit = detailQuery.data;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link to="/audit" className="text-sm text-[#1A7A4A]">
            ← Back to Audits
          </Link>
          <h1 className="mt-2 font-serif text-3xl font-bold text-[#1A1A18]">Franchise Operational Audit</h1>
        </div>
        <Link to="/audit">
          <Button variant="muted">Back</Button>
        </Link>
      </div>

      <div className="mb-4 grid gap-3 rounded-xl border border-[#E0DDD5] bg-white p-5 text-sm sm:grid-cols-2">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">Franchise</div>
          <div className="mt-1 font-semibold text-[#1A1A18]">{audit.franchise_name}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">Audit Date</div>
          <div className="mt-1 font-semibold text-[#1A1A18]">{formatAuditDate(audit.audit_date)}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">Auditor</div>
          <div className="mt-1 font-semibold text-[#1A1A18]">{audit.auditor_name}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">Overall Result</div>
          <div className="mt-1">
            <Badge tone={auditStatusTone(audit.overall_status)}>{auditStatusLabel(audit.overall_status)}</Badge>
          </div>
        </div>
      </div>

      <div className="mb-4 rounded-xl border border-[#E0DDD5] bg-white p-5">
        <h2 className="mb-3 font-serif text-xl font-bold text-[#1A1A18]">Checklist</h2>
        <div className="space-y-4">
          {audit.items.map((item) => (
            <div key={item.id} className="border-b border-[#E0DDD5] pb-4 last:border-b-0 last:pb-0">
              <div className="flex flex-wrap items-start gap-2">
                <span className="text-base font-semibold text-[#1A1A18]" aria-hidden>
                  {auditStatusIcon(item.status)}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-[#1A1A18]">{item.checklist_item}</div>
                  <div className="mt-1">
                    <Badge tone={auditStatusTone(item.status)}>{auditStatusLabel(item.status)}</Badge>
                  </div>
                  {item.remarks ? <p className="mt-2 text-sm text-[#4A4A46]">{item.remarks}</p> : null}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-[#E0DDD5] bg-white p-5">
        <h2 className="mb-2 font-serif text-xl font-bold text-[#1A1A18]">General Remarks</h2>
        <p className="text-sm text-[#4A4A46]">{audit.remarks || '—'}</p>
        <div className="mt-4 text-xs text-[#8A8A84]">Created: {formatAuditCreated(audit.created_at)}</div>
      </div>
    </div>
  );
}
