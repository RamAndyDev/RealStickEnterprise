import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CircleCheck, CircleMinus, MapPin, Store, UserRound } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import {
  ActionButton,
  ActionMenu,
  ActionMenuItem,
  ActionMenuSeparator,
  ActionSelect,
  ActionsTd,
  ActionsTh,
  AdminListCard,
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  FilterSelect,
  ListToolbar,
  Modal,
  PageHeader,
  StatCard,
  SuccessBanner,
  TableSkeleton,
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
import { LaunchProgressCompact } from './LaunchProgress';
import { franchiseLocationLine, franchiseSummaryCounts } from './franchiseListPresentation';
import { apiErrorMessage, statusLabel, statusTone } from './status';
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
import { paymentStateLabel, paymentStatusTone } from './offlinePayment';

function launchSource(item: Franchise) {
  return {
    status: item.status,
    payment_status: item.payment_status,
  };
}

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
  const summary = useMemo(() => franchiseSummaryCounts(items), [items]);

  function moreMenu(item: Franchise, includeStatus: boolean) {
    return (
      <ActionMenu label={`More actions for ${item.name}`}>
        <ActionMenuItem onClick={() => setEditTarget(item)}>Edit</ActionMenuItem>
        <ActionButton variant="muted" className="h-auto min-w-0 w-full justify-start border-0 bg-transparent px-3 py-2 text-left text-[13px] font-medium text-[#1A1A18] shadow-none hover:bg-[#F7F5F0]" onClick={() => resetOwnerForm(item)}>
          Create Owner
        </ActionButton>
        {includeStatus
          ? FRANCHISE_STATUSES.filter((status) => status !== item.status).map((status) => (
              <ActionMenuItem
                key={status}
                onClick={() => setStatusTarget({ franchise: item, next: status })}
              >
                {statusLabel(status)}
              </ActionMenuItem>
            ))
          : null}
        <ActionMenuSeparator />
        <ActionMenuItem
          destructive
          onClick={() => {
            setDeleteError(null);
            setDeleteTarget(item);
          }}
        >
          Delete
        </ActionMenuItem>
      </ActionMenu>
    );
  }

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="Franchise Management"
        description="Manage franchise outlets, owners, launch progress and payments."
        action={<Button onClick={() => setShowAdd(true)}>+ Add Outlet</Button>}
      />

      <FranchiseAuditSettings />

      {!listQuery.isError ? (
        <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            compact
            label="Total Outlets"
            value={listQuery.isLoading ? '—' : summary.total}
            color="navy"
            icon={<Store className="h-4 w-4" />}
          />
          <StatCard
            compact
            label="Active"
            value={listQuery.isLoading ? '—' : summary.active}
            color="green"
            icon={<CircleCheck className="h-4 w-4" />}
          />
          <StatCard
            compact
            label="Inactive"
            value={listQuery.isLoading ? '—' : summary.inactive}
            color="orange"
            icon={<CircleMinus className="h-4 w-4" />}
          />
          <StatCard
            compact
            label="Unassigned Owner"
            value={listQuery.isLoading ? '—' : summary.unassigned}
            color="mint"
            icon={<UserRound className="h-4 w-4" />}
          />
        </div>
      ) : null}

      <ListToolbar
        search={search}
        searchPlaceholder="Search outlets by name, city, code, or owner email"
        onSearchChange={setSearch}
        filters={
          <FilterSelect
            value={statusFilter}
            aria-label="Filter by status"
            onChange={(e) => setStatusFilter(e.target.value as FranchiseStatus | '')}
          >
            <option value="">All statuses</option>
            {FRANCHISE_STATUSES.map((status) => (
              <option key={status} value={status}>
                {statusLabel(status)}
              </option>
            ))}
          </FilterSelect>
        }
      />

      {feedback ? (
        <div className="mb-4">
          <SuccessBanner message={feedback} />
        </div>
      ) : null}
      {error && !ownerTarget && !showAdd && !deleteTarget ? (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      ) : null}

      {listQuery.isLoading ? <TableSkeleton /> : null}
      {listQuery.isError ? (
        <ErrorBanner message={apiErrorMessage(listQuery.error, 'Unable to load outlets.')} />
      ) : null}

      {!listQuery.isLoading && !listQuery.isError && items.length === 0 ? (
        <EmptyState
          title="No franchises found"
          hint="Try changing your search or add a new outlet."
          action={<Button onClick={() => setShowAdd(true)}>+ Add Outlet</Button>}
        />
      ) : null}

      {!listQuery.isLoading && items.length > 0 ? (
        <>
          <div className="hidden overflow-x-auto rounded-xl border border-[#E8E6E0] bg-white shadow-[0_1px_2px_rgba(0,0,0,.04)] lg:block">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-[#E8E6E0] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
                <tr>
                  <th className="w-[22%] px-5 py-3 font-semibold">Outlet</th>
                  <th className="w-[18%] px-5 py-3 font-semibold">Owner</th>
                  <th className="w-[16%] px-5 py-3 font-semibold">Contact</th>
                  <th className="w-[10%] px-5 py-3 font-semibold">Status</th>
                  <th className="w-[14%] min-w-[7.5rem] whitespace-nowrap px-5 py-3 font-semibold">Launch</th>
                  <th className="w-[10%] px-5 py-3 font-semibold">Payment</th>
                  <ActionsTh className="px-5" />
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const location = franchiseLocationLine(item);
                  return (
                    <tr
                      key={item.id}
                      className="border-b border-[#F0EEE8] last:border-b-0 hover:bg-[#FDFAF4]"
                    >
                      <td className="px-5 py-4 align-middle">
                        <div className="flex items-start gap-2.5">
                          <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[#F7F5F0] text-[#8A8A84]">
                            <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                          </span>
                          <div className="min-w-0">
                            <Link
                              to={`/franchises/${item.id}`}
                              className="text-[14px] font-semibold text-[#1A1A18] hover:text-[#1A7A4A]"
                            >
                              {item.name}
                            </Link>
                            {location ? (
                              <div className="mt-0.5 text-xs text-[#8A8A84]">{location}</div>
                            ) : null}
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-4 align-middle">
                        {item.owner?.full_name ? (
                          <>
                            <div className="text-[13px] text-[#1A1A18]">{item.owner.full_name}</div>
                            {item.owner_email || item.owner?.email ? (
                              <div className="mt-0.5 text-xs text-[#8A8A84]">
                                {item.owner_email || item.owner?.email}
                              </div>
                            ) : null}
                          </>
                        ) : (
                          <>
                            <Badge variant="soft" tone="muted">
                              {item.owner?.full_name ?? 'Unassigned'}
                            </Badge>
                            {item.owner_email ? (
                              <div className="mt-1 text-xs text-[#8A8A84]">{item.owner_email}</div>
                            ) : null}
                          </>
                        )}
                      </td>
                      <td className="px-5 py-4 align-middle text-[13px] text-[#5C5C56]">
                        {item.owner?.phone || item.owner_email || '—'}
                      </td>
                      <td className="px-5 py-4 align-middle">
                        <Badge variant="soft" tone={statusTone(item.status)}>
                          {statusLabel(item.status)}
                        </Badge>
                      </td>
                      <td className="whitespace-nowrap px-5 py-4 align-middle">
                        <LaunchProgressCompact source={launchSource(item)} showCount />
                      </td>
                      <td className="px-5 py-4 align-middle">
                        <Badge variant="soft" tone={paymentStatusTone(item.payment_status)}>
                          {paymentStateLabel(item.payment_status)}
                        </Badge>
                      </td>
                      <ActionsTd className="px-5 py-4">
                        <ActionButton
                          variant="outline"
                          onClick={() => navigate(`/franchises/${item.id}`)}
                        >
                          View
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
                        {moreMenu(item, false)}
                      </ActionsTd>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 lg:hidden">
            {items.map((item) => {
              const location = franchiseLocationLine(item);
              return (
                <AdminListCard key={`card-${item.id}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <Link
                        to={`/franchises/${item.id}`}
                        className="text-[15px] font-semibold text-[#1A1A18] hover:text-[#1A7A4A]"
                      >
                        {item.name}
                      </Link>
                      {location ? <div className="mt-0.5 text-xs text-[#8A8A84]">{location}</div> : null}
                    </div>
                    <Badge variant="soft" tone={statusTone(item.status)}>
                      {statusLabel(item.status)}
                    </Badge>
                  </div>

                  <dl className="mt-4 grid grid-cols-2 gap-x-3 gap-y-3 border-t border-[#F0EEE8] pt-3 text-sm">
                    <div>
                      <dt className="text-[10px] font-medium uppercase tracking-[.05em] text-[#8A8A84]">
                        Owner
                      </dt>
                      <dd className="mt-1 text-[13px] text-[#1A1A18]">
                        {item.owner?.full_name ?? 'Unassigned'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[10px] font-medium uppercase tracking-[.05em] text-[#8A8A84]">
                        Payment
                      </dt>
                      <dd className="mt-1">
                        <Badge variant="soft" tone={paymentStatusTone(item.payment_status)}>
                          {paymentStateLabel(item.payment_status)}
                        </Badge>
                      </dd>
                    </div>
                    <div className="col-span-2">
                      <dt className="text-[10px] font-medium uppercase tracking-[.05em] text-[#8A8A84]">
                        Launch
                      </dt>
                      <dd className="mt-1 whitespace-nowrap">
                        <LaunchProgressCompact source={launchSource(item)} showCount />
                      </dd>
                    </div>
                  </dl>

                  <div className="mt-4 flex items-center gap-1.5 border-t border-[#F0EEE8] pt-3">
                    <ActionButton
                      variant="outline"
                      onClick={() => navigate(`/franchises/${item.id}`)}
                    >
                      View
                    </ActionButton>
                    {moreMenu(item, true)}
                  </div>
                </AdminListCard>
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
