import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import {
  ActionButton,
  ActionSelect,
  ActionsTd,
  ActionsTh,
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  LoadingBlock,
  Modal,
  SuccessBanner,
} from '../../components/ui';
import {
  createFranchise,
  createFranchiseOwner,
  listFranchises,
  updateFranchise,
  updateFranchiseStatus,
} from '../../lib/franchisesApi';
import {
  FRANCHISE_STATUSES,
  type Franchise,
  type FranchiseStatus,
} from '../../types/franchise';
import {
  OutletForm,
  emptyOutletForm,
  franchiseToForm,
  toWritePayload,
  type OutletFormValues,
} from './OutletForm';
import { FranchiseAuditSettings } from './FranchiseAuditSettings';
import { LaunchProgressCompact, LaunchProgressDots } from './LaunchProgress';
import { deriveLaunchProgress } from './launchStages';
import { apiErrorMessage, formatDate, statusLabel, statusTone } from './status';
import {
  applyOwnerCreateResult,
  classifyOwnerCreateError,
  validateOwnerForm,
  type OwnerCreateFieldErrors,
} from '../users/ownerForm';

export function FranchisesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<FranchiseStatus | ''>('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [editTarget, setEditTarget] = useState<Franchise | null>(null);
  const [statusTarget, setStatusTarget] = useState<{
    franchise: Franchise;
    next: FranchiseStatus;
  } | null>(null);
  const [ownerTarget, setOwnerTarget] = useState<Franchise | null>(null);
  const [ownerEmail, setOwnerEmail] = useState('');
  const [ownerFullName, setOwnerFullName] = useState('');
  const [ownerPhone, setOwnerPhone] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createFieldErrors, setCreateFieldErrors] = useState<OwnerCreateFieldErrors>({});
  const [ownerFormError, setOwnerFormError] = useState<string | null>(null);
  const [ownerFieldErrors, setOwnerFieldErrors] = useState<OwnerCreateFieldErrors>({});

  useEffect(() => {
    const handle = window.setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => window.clearTimeout(handle);
  }, [search]);

  const listQuery = useQuery({
    queryKey: ['admin-franchises', debouncedSearch, statusFilter],
    queryFn: () =>
      listFranchises({
        search: debouncedSearch || undefined,
        status: statusFilter || undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (values: OutletFormValues) => createFranchise(toWritePayload(values, true)),
    onSuccess: async () => {
      const result = applyOwnerCreateResult(true);
      setShowAdd(false);
      setCreateError(result.error);
      setCreateFieldErrors({});
      setFeedback('Outlet added successfully.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-franchises'] });
    },
    onError: (err) => {
      const classified = classifyOwnerCreateError(err, {
        ownerLabels: true,
        fallback: 'Unable to add outlet.',
      });
      const result = applyOwnerCreateResult(false, classified.formError);
      setCreateError(result.error);
      setCreateFieldErrors(classified.fieldErrors);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: OutletFormValues }) =>
      updateFranchise(id, toWritePayload(values, false)),
    onSuccess: async () => {
      setEditTarget(null);
      setFeedback('Outlet updated successfully.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-franchises'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update outlet.')),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: FranchiseStatus }) =>
      updateFranchiseStatus(id, status),
    onSuccess: async (data) => {
      setStatusTarget(null);
      setFeedback(`Status changed to ${statusLabel(data.status)}.`);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-franchises'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to change status.')),
  });

  const createOwnerMutation = useMutation({
    mutationFn: ({
      id,
      full_name,
      email,
      phone,
    }: {
      id: string;
      full_name: string;
      email: string;
      phone?: string;
    }) => createFranchiseOwner(id, { full_name, email, phone }),
    onSuccess: async (data) => {
      const result = applyOwnerCreateResult(true);
      setOwnerTarget(null);
      setOwnerFullName('');
      setOwnerEmail('');
      setOwnerPhone('');
      setOwnerFormError(result.error);
      setOwnerFieldErrors({});
      setFeedback(data.message);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-franchises'] });
    },
    onError: (err) => {
      const classified = classifyOwnerCreateError(err, { ownerLabels: true });
      const result = applyOwnerCreateResult(false, classified.formError);
      setOwnerFormError(result.error);
      setOwnerFieldErrors(classified.fieldErrors);
    },
  });

  function resetOwnerForm(franchise: Franchise) {
    setOwnerTarget(franchise);
    setOwnerEmail(franchise.owner_email ?? '');
    setOwnerFullName('');
    setOwnerPhone('');
    setOwnerFormError(null);
    setOwnerFieldErrors({});
  }

  function clearOwnerSubmitError() {
    setOwnerFormError(null);
    setOwnerFieldErrors({});
  }

  function clearAddSubmitError() {
    setCreateError(null);
    setCreateFieldErrors({});
  }

  function closeAdd() {
    setShowAdd(false);
    clearAddSubmitError();
  }

  const items = listQuery.data?.items ?? [];
  const activeCount = items.filter((item) => item.status === 'ACTIVE').length;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">Franchise Outlets</h1>
          <p className="text-xs text-[#8A8A84]">
            {listQuery.isLoading ? 'Loading…' : `${activeCount} active`}
          </p>
        </div>
        <Button onClick={() => setShowAdd(true)}>+ Add Outlet</Button>
      </div>

      <FranchiseAuditSettings />

      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_220px]">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search outlets by name, city, code, or owner email"
          className="w-full rounded-lg border border-[#E0DDD5] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1A7A4A]"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as FranchiseStatus | '')}
          className="w-full rounded-lg border border-[#E0DDD5] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1A7A4A]"
        >
          <option value="">All statuses</option>
          {FRANCHISE_STATUSES.map((status) => (
            <option key={status} value={status}>
              {statusLabel(status)}
            </option>
          ))}
        </select>
      </div>

      {feedback ? (
        <div className="mb-3">
          <SuccessBanner message={feedback} />
        </div>
      ) : null}
      {error && !ownerTarget && !showAdd ? (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      ) : null}

      {listQuery.isLoading ? <LoadingBlock label="Loading franchise outlets…" /> : null}
      {listQuery.isError ? (
        <ErrorBanner message={apiErrorMessage(listQuery.error, 'Unable to load outlets.')} />
      ) : null}

      {!listQuery.isLoading && !listQuery.isError && items.length === 0 ? (
        <EmptyState
          title="No outlets yet"
          hint="Add the first outlet to begin franchise management."
        />
      ) : null}

      {!listQuery.isLoading && items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-[#E0DDD5] bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
              <tr>
                <th className="px-4 py-3 font-semibold">Outlet</th>
                <th className="px-4 py-3 font-semibold">Tier</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Owner</th>
                <th className="px-4 py-3 font-semibold">Payment</th>
                <th className="px-4 py-3 font-semibold">Launch</th>
                <th className="px-4 py-3 font-semibold">Open</th>
                <ActionsTh />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-[#E0DDD5] last:border-b-0">
                  <td className="px-4 py-3">
                    <Link
                      to={`/franchises/${item.id}`}
                      className="font-semibold text-[#1A7A4A] hover:underline"
                    >
                      {item.name}
                    </Link>
                    <div className="text-xs text-[#8A8A84]">
                      {[item.city, item.tier ? `${item.tier} Partner` : null]
                        .filter(Boolean)
                        .join(' · ')}
                    </div>
                    {item.address ? (
                      <div className="mt-0.5 text-[11px] text-[#8A8A84]">{item.address}</div>
                    ) : null}
                  </td>
                  <td className="px-4 py-3">{item.tier ?? '—'}</td>
                  <td className="px-4 py-3">
                    <Badge tone={statusTone(item.status)}>{statusLabel(item.status)}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div>{item.owner?.full_name ?? 'Unassigned'}</div>
                    <div className="text-xs text-[#8A8A84]">{item.owner_email ?? '—'}</div>
                  </td>
                  <td className="px-4 py-3">{item.payment_status ?? '—'}</td>
                  <td className="px-4 py-3">
                    <LaunchProgressCompact
                      source={{
                        status: item.status,
                        payment_status: item.payment_status,
                      }}
                    />
                  </td>
                  <td className="px-4 py-3">{formatDate(item.open_date)}</td>
                  <ActionsTd>
                    <ActionButton
                      variant="outline"
                      onClick={() => navigate(`/franchises/${item.id}`)}
                    >
                      View
                    </ActionButton>
                    <ActionButton variant="outline" onClick={() => setEditTarget(item)}>
                      Edit
                    </ActionButton>
                    <ActionButton variant="outline" onClick={() => resetOwnerForm(item)}>
                      Create Owner
                    </ActionButton>
                    <ActionSelect
                      value=""
                      aria-label={`Change status for ${item.name}`}
                      onChange={(e) => {
                        const next = e.target.value as FranchiseStatus;
                        if (!next) return;
                        setStatusTarget({ franchise: item, next });
                      }}
                    >
                      <option value="">Status…</option>
                      {FRANCHISE_STATUSES.filter((s) => s !== item.status).map((status) => (
                        <option key={status} value={status}>
                          {statusLabel(status)}
                        </option>
                      ))}
                    </ActionSelect>
                  </ActionsTd>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {/* Prototype-style outlet cards for at-a-glance view */}
      {!listQuery.isLoading && items.length > 0 ? (
        <div className="mt-6 grid grid-cols-[repeat(auto-fill,minmax(250px,1fr))] gap-3">
          {items.map((item) => {
            const launch = deriveLaunchProgress({
              status: item.status,
              payment_status: item.payment_status,
            });
            return (
            <button
              key={`card-${item.id}`}
              type="button"
              onClick={() => navigate(`/franchises/${item.id}`)}
              className="overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white text-left"
            >
              <div
                className="px-3 py-2.5"
                style={{
                  background: item.status === 'ACTIVE' ? '#0D4F2E' : '#8A8A84',
                }}
              >
                <div className="text-[13px] font-bold text-white">{item.name}</div>
                <div className="mt-0.5 text-[10px] text-white/55">
                  {item.city || '—'} · {item.tier || 'Partner'} Partner
                </div>
              </div>
              <div className="px-3 py-2.5">
                <div className="mb-2 grid grid-cols-2 gap-2">
                  <div className="rounded-md bg-[#FDFAF4] p-2 text-center">
                    <div className="font-serif text-[15px] font-bold text-[#1A7A4A]">
                      {statusLabel(item.status)}
                    </div>
                    <div className="text-[9px] uppercase tracking-[.05em] text-[#8A8A84]">Status</div>
                  </div>
                  <div className="rounded-md bg-[#FDFAF4] p-2 text-center">
                    <div className="mb-1 flex justify-center">
                      <LaunchProgressDots progress={launch} />
                    </div>
                    <div className="font-serif text-[13px] font-bold text-[#E8621A]">
                      {launch.currentShortLabel}
                    </div>
                    <div className="text-[9px] uppercase tracking-[.05em] text-[#8A8A84]">Launch</div>
                  </div>
                </div>
                <div className="text-[10px] text-[#8A8A84]">{item.address || 'No address'}</div>
              </div>
            </button>
            );
          })}
        </div>
      ) : null}

      {showAdd ? (
        <Modal title="Add Outlet" wide onClose={closeAdd}>
          <OutletForm
            mode="create"
            initial={emptyOutletForm()}
            submitting={createMutation.isPending}
            formError={createError}
            apiFieldErrors={createFieldErrors}
            onCancel={closeAdd}
            onClearSubmitError={clearAddSubmitError}
            onSubmit={(values) => createMutation.mutate(values)}
          />
        </Modal>
      ) : null}

      {editTarget ? (
        <Modal title="Edit Outlet" wide onClose={() => setEditTarget(null)}>
          <OutletForm
            mode="edit"
            initial={franchiseToForm(editTarget)}
            submitting={updateMutation.isPending}
            onCancel={() => setEditTarget(null)}
            onSubmit={(values) => updateMutation.mutate({ id: editTarget.id, values })}
          />
        </Modal>
      ) : null}

      {statusTarget ? (
        <Modal title="Confirm status change" onClose={() => setStatusTarget(null)}>
          <p className="mb-4 text-sm text-[#4A4A46]">
            Change <strong>{statusTarget.franchise.name}</strong> from{' '}
            <strong>{statusLabel(statusTarget.franchise.status)}</strong> to{' '}
            <strong>{statusLabel(statusTarget.next)}</strong>?
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={() => setStatusTarget(null)}>
              Cancel
            </Button>
            <Button
              variant={statusTarget.next === 'SUSPENDED' || statusTarget.next === 'CLOSED' ? 'danger' : 'primary'}
              disabled={statusMutation.isPending}
              onClick={() =>
                statusMutation.mutate({
                  id: statusTarget.franchise.id,
                  status: statusTarget.next,
                })
              }
            >
              {statusMutation.isPending ? 'Updating…' : 'Confirm'}
            </Button>
          </div>
        </Modal>
      ) : null}

      {ownerTarget ? (
        <Modal
          title="Create Franchise Owner"
          onClose={() => {
            setOwnerTarget(null);
            clearOwnerSubmitError();
          }}
        >
          <p className="mb-3 text-sm text-[#4A4A46]">
            Create an owner for <strong>{ownerTarget.name}</strong>. Passwords are never stored in
            profiles or shown in this UI.
          </p>

          {ownerFormError ? (
            <div className="mb-3">
              <ErrorBanner message={ownerFormError} />
            </div>
          ) : null}

          <Field
            label="Owner Name"
            value={ownerFullName}
            error={ownerFieldErrors.full_name}
            onChange={(e) => {
              setOwnerFullName(e.target.value);
              if (ownerFieldErrors.full_name || ownerFormError) {
                setOwnerFieldErrors((current) => {
                  if (!current.full_name) return current;
                  const next = { ...current };
                  delete next.full_name;
                  return next;
                });
                setOwnerFormError(null);
              }
            }}
            required
          />
          <Field
            label="Owner Email"
            type="email"
            value={ownerEmail}
            error={ownerFieldErrors.email}
            onChange={(e) => {
              setOwnerEmail(e.target.value);
              if (ownerFieldErrors.email || ownerFormError) {
                setOwnerFieldErrors((current) => {
                  if (!current.email) return current;
                  const next = { ...current };
                  delete next.email;
                  return next;
                });
                setOwnerFormError(null);
              }
            }}
            required
          />
          <Field
            label="Phone"
            value={ownerPhone}
            onChange={(e) => setOwnerPhone(e.target.value)}
          />
          <p className="mb-4 text-xs text-[#8A8A84]">
            Supabase Auth will email a secure password setup / invite link. No permanent
            password is displayed here.
          </p>
          <div className="flex justify-end gap-2">
            <Button
              variant="muted"
              onClick={() => {
                setOwnerTarget(null);
                clearOwnerSubmitError();
              }}
            >
              Cancel
            </Button>
            <Button
              disabled={createOwnerMutation.isPending}
              onClick={() => {
                const errors = validateOwnerForm(
                  {
                    full_name: ownerFullName,
                    email: ownerEmail,
                    role: 'FRANCHISE_OWNER',
                    franchise_id: ownerTarget.id,
                  },
                  { ownerLabels: true, requireFranchise: false },
                );
                setOwnerFieldErrors(errors);
                if (Object.keys(errors).length > 0) {
                  setOwnerFormError(null);
                  return;
                }
                setOwnerFormError(null);
                createOwnerMutation.mutate({
                  id: ownerTarget.id,
                  full_name: ownerFullName.trim(),
                  email: ownerEmail.trim(),
                  phone: ownerPhone.trim() || undefined,
                });
              }}
            >
              {createOwnerMutation.isPending ? 'Creating…' : 'Create Owner'}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
