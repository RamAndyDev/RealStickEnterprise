import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';

import { Badge, Button, ErrorBanner, Field, SelectField } from '../../components/ui';
import { useAuth } from '../auth/AuthProvider';
import { createAudit } from '../../lib/auditsApi';
import { listFranchises } from '../../lib/franchisesApi';
import { apiErrorMessage } from '../franchises/status';
import {
  FRANCHISE_OPERATIONAL_CHECKLIST,
  auditStatusLabel,
  auditStatusTone,
  calculateOverallStatus,
  utcTodayIso,
  type FranchiseAuditStatus,
} from '../../types/audit';

type ItemDraft = {
  status: FranchiseAuditStatus | '';
  remarks: string;
};

function emptyItems(): Record<string, ItemDraft> {
  return Object.fromEntries(
    FRANCHISE_OPERATIONAL_CHECKLIST.map((item) => [item.item_key, { status: '', remarks: '' }]),
  );
}

const STATUS_OPTIONS: FranchiseAuditStatus[] = ['PASS', 'NEEDS_ATTENTION', 'FAIL'];

export function CreateAuditPage() {
  const { profile } = useAuth();
  const navigate = useNavigate();
  const isAdmin = profile?.role === 'SYSTEM_ADMIN';
  const today = utcTodayIso();

  const [franchiseId, setFranchiseId] = useState('');
  const [auditDate, setAuditDate] = useState(today);
  const [remarks, setRemarks] = useState('');
  const [items, setItems] = useState<Record<string, ItemDraft>>(emptyItems);
  const [error, setError] = useState<string | null>(null);

  const franchisesQuery = useQuery({
    queryKey: ['admin-franchises-options'],
    queryFn: () => listFranchises({ include_archived: true }),
    enabled: isAdmin,
  });

  const franchises = useMemo(
    () => [...(franchisesQuery.data?.items ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
    [franchisesQuery.data?.items],
  );

  const overall = calculateOverallStatus(FRANCHISE_OPERATIONAL_CHECKLIST.map((item) => items[item.item_key].status));
  const allSelected = FRANCHISE_OPERATIONAL_CHECKLIST.every((item) => items[item.item_key].status);

  const mutation = useMutation({
    mutationFn: () =>
      createAudit({
        franchise_id: isAdmin ? franchiseId : undefined,
        audit_date: auditDate,
        remarks: remarks.trim() || null,
        items: FRANCHISE_OPERATIONAL_CHECKLIST.map((item) => ({
          item_key: item.item_key,
          status: items[item.item_key].status as FranchiseAuditStatus,
          remarks: items[item.item_key].remarks.trim() || null,
        })),
      }),
    onSuccess: (created) => {
      navigate(`/audit/${created.id}`);
    },
    onError: (err) => {
      setError(apiErrorMessage(err, 'Unable to save audit.'));
    },
  });

  function setItemStatus(itemKey: string, status: FranchiseAuditStatus) {
    setItems((current) => ({
      ...current,
      [itemKey]: { ...current[itemKey], status },
    }));
  }

  function setItemRemarks(itemKey: string, value: string) {
    setItems((current) => ({
      ...current,
      [itemKey]: { ...current[itemKey], remarks: value },
    }));
  }

  function onSubmit() {
    setError(null);
    if (isAdmin && !franchiseId) {
      setError('Select a franchise.');
      return;
    }
    if (!auditDate) {
      setError('Audit date is required.');
      return;
    }
    if (auditDate > today) {
      setError('Audit date cannot be in the future.');
      return;
    }
    if (!allSelected) {
      setError('Every checklist item needs a status.');
      return;
    }
    mutation.mutate();
  }

  return (
    <div className="mx-auto max-w-4xl">
      <Link to="/audit" className="text-sm text-[#1A7A4A]">
        ← Back to Audits
      </Link>
      <h1 className="mt-2 font-serif text-2xl font-bold text-[#1A1A18]">Create Audit</h1>
      <p className="mt-1 text-sm text-[#8A8A84]">
        Complete all 10 checklist items. Overall result is calculated automatically.
      </p>

      {error ? (
        <div className="mt-4">
          <ErrorBanner message={error} />
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 rounded-xl border border-[#E0DDD5] bg-white p-4 sm:grid-cols-2">
        {isAdmin ? (
          <SelectField
            label="Franchise"
            value={franchiseId}
            onChange={(event) => setFranchiseId(event.target.value)}
          >
            <option value="">Select franchise</option>
            {franchises.map((franchise) => (
              <option key={franchise.id} value={franchise.id}>
                {franchise.name}
              </option>
            ))}
          </SelectField>
        ) : (
          <Field label="Franchise" value={profile?.franchise_name || 'Your franchise'} readOnly disabled />
        )}
        <Field
          label="Audit Date"
          type="date"
          value={auditDate}
          max={today}
          onChange={(event) => setAuditDate(event.target.value > today ? today : event.target.value)}
        />
        <div className="sm:col-span-2">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
            Overall Result
          </div>
          {overall ? (
            <Badge tone={auditStatusTone(overall)}>{auditStatusLabel(overall)}</Badge>
          ) : (
            <span className="text-sm text-[#8A8A84]">Select checklist statuses</span>
          )}
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {FRANCHISE_OPERATIONAL_CHECKLIST.map((item) => {
          const draft = items[item.item_key];
          return (
            <div key={item.item_key} className="rounded-xl border border-[#E0DDD5] bg-white p-4">
              <div className="text-sm font-semibold text-[#1A1A18]">{item.label}</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {STATUS_OPTIONS.map((status) => {
                  const selected = draft.status === status;
                  return (
                    <button
                      key={status}
                      type="button"
                      onClick={() => setItemStatus(item.item_key, status)}
                      className={`rounded-lg border-2 px-3 py-2 text-[12px] font-bold tracking-[.04em] ${
                        selected
                          ? status === 'PASS'
                            ? 'border-[#1A7A4A] bg-[#1A7A4A] text-white'
                            : status === 'NEEDS_ATTENTION'
                              ? 'border-[#D97706] bg-[#D97706] text-white'
                              : 'border-[#C00000] bg-[#C00000] text-white'
                          : 'border-[#E0DDD5] bg-white text-[#4A4A46] hover:bg-[#FDFAF4]'
                      }`}
                    >
                      {auditStatusLabel(status)}
                    </button>
                  );
                })}
              </div>
              <label className="mt-3 block">
                <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
                  Remarks
                </span>
                <input
                  className="w-full rounded-lg border border-[#E0DDD5] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1A7A4A]"
                  value={draft.remarks}
                  onChange={(event) => setItemRemarks(item.item_key, event.target.value)}
                  placeholder="Optional"
                />
              </label>
            </div>
          );
        })}
      </div>

      <label className="mt-5 block rounded-xl border border-[#E0DDD5] bg-white p-4">
        <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
          General Remarks
        </span>
        <textarea
          className="min-h-[96px] w-full rounded-lg border border-[#E0DDD5] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1A7A4A]"
          value={remarks}
          onChange={(event) => setRemarks(event.target.value)}
          placeholder="Optional"
        />
      </label>

      <div className="mt-5 flex flex-wrap gap-3">
        <Button variant="muted" onClick={() => navigate('/audit')}>
          Cancel
        </Button>
        <Button onClick={onSubmit} disabled={mutation.isPending}>
          {mutation.isPending ? 'Saving…' : 'Save Audit'}
        </Button>
      </div>
    </div>
  );
}
