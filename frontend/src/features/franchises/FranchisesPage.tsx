import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import {
  ActionButton,
  ActionMenu,
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
  deleteFranchise,
  listFranchises,
  updateFranchise,
  updateFranchiseStatus,
} from '../../lib/franchisesApi';
import { safeApiErrorMessage } from '../../lib/validation';
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
import {
  DELETE_FRANCHISE_CONFIRM_MESSAGE,
  DELETE_FRANCHISE_FALLBACK,
  DELETE_FRANCHISE_SUCCESS,
  DELETE_FRANCHISE_TITLE,
  applyDeleteFranchiseResult,
} from './deleteFranchise';

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
  const [deleteTarget, setDeleteTarget] = useState<Franchise | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
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

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteFranchise(id),
    onSuccess: async () => {
      const result = applyDeleteFranchiseResult(true);
      setDeleteError(result.error);
      setDeleteTarget(null);
      setFeedback(DELETE_FRANCHISE_SUCCESS);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-franchises'] });
    },
    onError: (err) => {
      const result = applyDeleteFranchiseResult(
        false,
        safeApiErrorMessage(err, DELETE_FRANCHISE_FALLBACK),
      );
      setDeleteError(result.error);
    },
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
      {error && !ownerTarget && !showAdd && !deleteTarget ? (
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
        <>
          <div className="hidden overflow-x-auto rounded-xl border border-[#E0DDD5] bg-white md:block">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
                <tr>
                  <th className="px-4 py-3 font-semibold">Outlet</th>
                  <th className="px-4 py-3 font-semibold">Owner</th>
                  <th className="px-4 py-3 font-semibold">Contact</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Launch</th>
                  <th className="px-4 py-3 font-semibold">Payment</th>
                  <ActionsTh />
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-[#E0DDD5] last:border-b-0">
                    <td className="px-4 py-3 align-top">
                      <Link
                        to={`/franchises/${item.id}`}
                        className="font-semibold text-[#1A7A4A] hover:underline"
                      >
                        {item.name}
                      </Link>
                      <div className="mt-0.5 text-xs text-[#8A8A84]">
                        {[item.city, item.tier ? `${item.tier} Partner` : null]
                          .filter(Boolean)
                          .join(' · ')}
                      </div>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <div className="font-medium text-[#1A1A18]">
                        {item.owner?.full_name ?? 'Unassigned'}
                      </div>
                      {item.owner_email ? (
                        <div className="mt-0.5 text-xs text-[#8A8A84]">{item.owner_email}</div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 align-top text-[#4A4A46]">
                      {item.owner?.phone || item.owner_email || '—'}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <Badge tone={statusTone(item.status)}>{statusLabel(item.status)}</Badge>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <LaunchProgressCompact
                        source={{
                          status: item.status,
                          payment_status: item.payment_status,
                        }}
                      />
                    </td>
                    <td className="px-4 py-3 align-top text-[#4A4A46]">
                      {item.payment_status ?? '—'}
                    </td>
                    <ActionsTd>
                      <ActionButton variant="outline" onClick={() => setEditTarget(item)}>
                        Edit
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
                        <option value="">
                          {item.status === 'ACTIVE' ? 'Deactivate…' : 'Activate…'}
                        </option>
                        {FRANCHISE_STATUSES.filter((s) => s !== item.status).map((status) => (
                          <option key={status} value={status}>
                            {statusLabel(status)}
                          </option>
                        ))}
                      </ActionSelect>
                      <ActionMenu>
                        <ActionButton variant="outline" onClick={() => resetOwnerForm(item)}>
                          Create Owner
                        </ActionButton>
                        <ActionButton
                          variant="danger"
                          onClick={() => {
                            setDeleteError(null);
                            setDeleteTarget(item);
                          }}
                        >
                          Delete
                        </ActionButton>
                        <ActionButton
                          variant="muted"
                          onClick={() => navigate(`/franchises/${item.id}`)}
                        >
                          View
                        </ActionButton>
                      </ActionMenu>
                    </ActionsTd>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 md:hidden">
            {items.map((item) => {
              const launch = deriveLaunchProgress({
                status: item.status,
                payment_status: item.payment_status,
              });
              return (
                <article
                  key={`card-${item.id}`}
                  className="overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white"
                >
                  <div
                    className="px-4 py-3"
                    style={{
                      background: item.status === 'ACTIVE' ? '#0D4F2E' : '#8A8A84',
                    }}
                  >
                    <Link
                      to={`/franchises/${item.id}`}
                      className="text-[15px] font-bold text-white hover:underline"
                    >
                      {item.name}
                    </Link>
                    <div className="mt-0.5 text-[11px] text-white/70">
                      {item.city || '—'}
                      {item.tier ? ` · ${item.tier} Partner` : ''}
                    </div>
                  </div>
                  <div className="space-y-3 px-4 py-3">
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <div className="text-[10px] font-semibold uppercase tracking-[.05em] text-[#8A8A84]">
                          Owner
                        </div>
                        <div className="mt-0.5 font-medium">
                          {item.owner?.full_name ?? 'Unassigned'}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] font-semibold uppercase tracking-[.05em] text-[#8A8A84]">
                          Contact
                        </div>
                        <div className="mt-0.5">{item.owner?.phone || item.owner_email || '—'}</div>
                      </div>
                      <div>
                        <div className="text-[10px] font-semibold uppercase tracking-[.05em] text-[#8A8A84]">
                          Status
                        </div>
                        <div className="mt-1">
                          <Badge tone={statusTone(item.status)}>{statusLabel(item.status)}</Badge>
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] font-semibold uppercase tracking-[.05em] text-[#8A8A84]">
                          Payment
                        </div>
                        <div className="mt-0.5">{item.payment_status ?? '—'}</div>
                      </div>
                    </div>
                    <div className="flex items-center justify-between rounded-md bg-[#FDFAF4] px-3 py-2">
                      <LaunchProgressDots progress={launch} />
                      <div className="text-right">
                        <div className="font-serif text-sm font-bold text-[#E8621A]">
                          {launch.currentShortLabel}
                        </div>
                        <div className="text-[9px] uppercase tracking-[.05em] text-[#8A8A84]">
                          Launch
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <ActionButton variant="outline" onClick={() => setEditTarget(item)}>
                        Edit
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
                        <option value="">
                          {item.status === 'ACTIVE' ? 'Deactivate…' : 'Activate…'}
                        </option>
                        {FRANCHISE_STATUSES.filter((s) => s !== item.status).map((status) => (
                          <option key={status} value={status}>
                            {statusLabel(status)}
                          </option>
                        ))}
                      </ActionSelect>
                      <ActionButton variant="outline" onClick={() => resetOwnerForm(item)}>
                        Create Owner
                      </ActionButton>
                      <ActionButton
                        variant="danger"
                        onClick={() => {
                          setDeleteError(null);
                          setDeleteTarget(item);
                        }}
                      >
                        Delete
                      </ActionButton>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </>
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
            error={ownerFieldErrors.phone}
            placeholder="+919876543210"
            onChange={(e) => {
              setOwnerPhone(e.target.value);
              if (ownerFieldErrors.phone || ownerFormError) {
                setOwnerFieldErrors((current) => {
                  if (!current.phone) return current;
                  const next = { ...current };
                  delete next.phone;
                  return next;
                });
                setOwnerFormError(null);
              }
            }}
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
                    phone: ownerPhone,
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

      {deleteTarget ? (
        <Modal
          title={DELETE_FRANCHISE_TITLE}
          onClose={() => {
            setDeleteTarget(null);
            setDeleteError(null);
          }}
        >
          <p className="text-sm text-[#1A1A18]">{DELETE_FRANCHISE_CONFIRM_MESSAGE}</p>
          <p className="mt-1 text-sm font-medium text-[#5C5C56]">{deleteTarget.name}</p>
          {deleteError ? (
            <div className="mt-3">
              <ErrorBanner message={deleteError} />
            </div>
          ) : null}
          <div className="mt-4 flex justify-end gap-2">
            <Button
              variant="muted"
              onClick={() => {
                setDeleteTarget(null);
                setDeleteError(null);
              }}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(deleteTarget.id)}
            >
              {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
