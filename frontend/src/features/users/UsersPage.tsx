import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

import {
  ActionButton,
  ActionMenu,
  ActionMenuItem,
  ActionMenuSeparator,
  ActionsTd,
  ActionsTh,
  AdminListCard,
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  InitialsAvatar,
  ListToolbar,
  Modal,
  PageHeader,
  SegmentedTabs,
  SuccessBanner,
  TableSkeleton,
} from '../../components/ui';
import { listFranchises } from '../../lib/franchisesApi';
import { safeApiErrorMessage } from '../../lib/validation';
import {
  createAdminUser,
  deleteAdminUser,
  listAdminUsers,
  resetAdminUserPassword,
  updateAdminUser,
} from '../../lib/usersApi';
import type { UserRole } from '../../types/auth';
import type { ManagedUser } from '../../types/user';
import { apiErrorMessage } from '../franchises/status';
import { roleLabel, roleTone } from './labels';
import {
  applyOwnerCreateResult,
  classifyOwnerCreateError,
  type OwnerCreateFieldErrors,
} from './ownerForm';
import {
  DELETE_USER_CONFIRM_MESSAGE,
  DELETE_USER_FALLBACK,
  DELETE_USER_SUCCESS,
  DELETE_USER_TITLE,
  applyDeleteUserResult,
} from './deleteUser';
import { managedUserContact, managedUserFranchiseLabel } from './userListPresentation';
import { UserDetail } from './UserDetail';
import { UserForm, emptyUserForm, userToForm, type UserFormValues } from './UserForm';

const ROLE_TABS: { id: '' | UserRole; label: string }[] = [
  { id: '', label: 'All' },
  { id: 'SYSTEM_ADMIN', label: 'Administrators' },
  { id: 'FRANCHISE_OWNER', label: 'Franchise Owners' },
];

export function UsersPage() {
  const queryClient = useQueryClient();
  const [roleFilter, setRoleFilter] = useState<'' | UserRole>('');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [viewTarget, setViewTarget] = useState<ManagedUser | null>(null);
  const [editTarget, setEditTarget] = useState<ManagedUser | null>(null);
  const [statusTarget, setStatusTarget] = useState<ManagedUser | null>(null);
  const [resetTarget, setResetTarget] = useState<ManagedUser | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ManagedUser | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createFieldErrors, setCreateFieldErrors] = useState<OwnerCreateFieldErrors>({});

  useEffect(() => {
    const handle = window.setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => window.clearTimeout(handle);
  }, [search]);

  const listQuery = useQuery({
    queryKey: ['admin-users', roleFilter, debouncedSearch],
    queryFn: () =>
      listAdminUsers({
        role: roleFilter,
        search: debouncedSearch || undefined,
      }),
  });

  const franchisesQuery = useQuery({
    queryKey: ['admin-franchises-options'],
    queryFn: () => listFranchises({ include_archived: true }),
  });

  const createMutation = useMutation({
    mutationFn: (values: UserFormValues) =>
      createAdminUser({
        full_name: values.full_name.trim(),
        email: values.email.trim(),
        phone: values.phone.trim() || null,
        role: values.role,
        franchise_id: values.role === 'SYSTEM_ADMIN' ? null : values.franchise_id,
      }),
    onSuccess: async (data) => {
      const result = applyOwnerCreateResult(true);
      setShowAdd(false);
      setCreateError(result.error);
      setCreateFieldErrors({});
      setFeedback(data.message);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: (err) => {
      const classified = classifyOwnerCreateError(err);
      const result = applyOwnerCreateResult(false, classified.formError);
      setCreateError(result.error);
      setCreateFieldErrors(classified.fieldErrors);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: UserFormValues }) =>
      updateAdminUser(id, {
        full_name: values.full_name.trim(),
        phone: values.phone.trim() || null,
        franchise_id:
          values.role === 'SYSTEM_ADMIN' ? undefined : values.franchise_id || undefined,
      }),
    onSuccess: async () => {
      setEditTarget(null);
      setFeedback('User updated.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update user.')),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateAdminUser(id, { is_active }),
    onSuccess: async (data) => {
      setStatusTarget(null);
      setFeedback(`${data.full_name} is now ${data.is_active ? 'active' : 'inactive'}.`);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update user status.')),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAdminUser(id),
    onSuccess: async () => {
      const result = applyDeleteUserResult(true);
      setDeleteError(result.error);
      setDeleteTarget(null);
      setFeedback(DELETE_USER_SUCCESS);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: (err) => {
      const result = applyDeleteUserResult(false, safeApiErrorMessage(err, DELETE_USER_FALLBACK));
      setDeleteError(result.error);
    },
  });

  const resetMutation = useMutation({
    mutationFn: (id: string) => resetAdminUserPassword(id),
    onSuccess: async (data) => {
      setResetTarget(null);
      setFeedback(data.message);
      setError(null);
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to reset password.')),
  });

  const items = listQuery.data?.items ?? [];
  const franchises = franchisesQuery.data?.items ?? [];
  const createInitial = useMemo(
    () => emptyUserForm(roleFilter || 'SYSTEM_ADMIN'),
    [roleFilter],
  );

  function openAdd() {
    setCreateError(null);
    setCreateFieldErrors({});
    setShowAdd(true);
  }

  function moreMenu(item: ManagedUser) {
    return (
      <ActionMenu label={`More actions for ${item.full_name}`}>
        <ActionMenuItem onClick={() => setViewTarget(item)}>View</ActionMenuItem>
        <ActionMenuItem onClick={() => setEditTarget(item)}>Edit</ActionMenuItem>
        <ActionMenuItem onClick={() => setResetTarget(item)}>Reset Password</ActionMenuItem>
        <ActionMenuItem onClick={() => setStatusTarget(item)}>
          {item.is_active ? 'Deactivate' : 'Activate'}
        </ActionMenuItem>
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
        title="User Management"
        description="Manage system administrators and franchise owners."
        action={<Button onClick={openAdd}>+ Add User</Button>}
      />

      <SegmentedTabs items={ROLE_TABS} value={roleFilter} onChange={setRoleFilter} />

      <ListToolbar
        search={search}
        searchPlaceholder="Search by name, email, phone, or franchise"
        onSearchChange={setSearch}
      />

      {feedback ? (
        <div className="mb-4">
          <SuccessBanner message={feedback} />
        </div>
      ) : null}
      {error && !showAdd && !deleteTarget ? (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      ) : null}

      {listQuery.isLoading ? <TableSkeleton /> : null}
      {listQuery.isError ? (
        <ErrorBanner message={apiErrorMessage(listQuery.error, 'Unable to load users.')} />
      ) : null}

      {!listQuery.isLoading && !listQuery.isError && items.length === 0 ? (
        <EmptyState
          title="No users found"
          hint="Try changing your filters or add a new user."
          action={<Button onClick={openAdd}>+ Add User</Button>}
        />
      ) : null}

      {!listQuery.isLoading && items.length > 0 ? (
        <>
          <div className="hidden overflow-x-auto rounded-xl border border-[#E8E6E0] bg-white shadow-[0_1px_2px_rgba(0,0,0,.04)] lg:block">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-[#E8E6E0] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
                <tr>
                  <th className="w-[28%] px-5 py-3 font-semibold">User</th>
                  <th className="w-[14%] px-5 py-3 font-semibold">Role</th>
                  <th className="w-[18%] px-5 py-3 font-semibold">Franchise</th>
                  <th className="w-[16%] px-5 py-3 font-semibold">Contact</th>
                  <th className="w-[10%] px-5 py-3 font-semibold">Status</th>
                  <ActionsTh className="px-5" />
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-[#F0EEE8] last:border-b-0 hover:bg-[#FDFAF4]"
                  >
                    <td className="px-5 py-4 align-middle">
                      <button
                        type="button"
                        className="flex items-center gap-3 rounded-md text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A]"
                        onClick={() => setViewTarget(item)}
                      >
                        <InitialsAvatar name={item.full_name} />
                        <span className="min-w-0">
                          <span className="block text-[14px] font-semibold text-[#1A1A18]">
                            {item.full_name}
                          </span>
                          <span className="mt-0.5 block text-xs text-[#8A8A84]">
                            {item.email ?? '—'}
                          </span>
                        </span>
                      </button>
                    </td>
                    <td className="px-5 py-4 align-middle">
                      <Badge variant="soft" tone={roleTone(item.role)}>
                        {roleLabel(item.role)}
                      </Badge>
                    </td>
                    <td className="px-5 py-4 align-middle text-[13px] text-[#4A4A46]">
                      {managedUserFranchiseLabel(item)}
                    </td>
                    <td className="px-5 py-4 align-middle text-[13px] text-[#5C5C56]">
                      {managedUserContact(item)}
                    </td>
                    <td className="px-5 py-4 align-middle">
                      <Badge variant="soft" tone={item.is_active ? 'green' : 'muted'}>
                        {item.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <ActionsTd className="px-5 py-4">
                      <ActionButton variant="outline" onClick={() => setEditTarget(item)}>
                        Edit
                      </ActionButton>
                      {moreMenu(item)}
                    </ActionsTd>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 lg:hidden">
            {items.map((item) => (
              <AdminListCard key={`card-${item.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <button
                    type="button"
                    className="flex min-w-0 items-center gap-3 rounded-md text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A]"
                    onClick={() => setViewTarget(item)}
                  >
                    <InitialsAvatar name={item.full_name} />
                    <span className="min-w-0">
                      <span className="block text-[15px] font-semibold text-[#1A1A18]">
                        {item.full_name}
                      </span>
                      <span className="mt-0.5 block text-xs text-[#8A8A84]">{item.email ?? '—'}</span>
                    </span>
                  </button>
                  <Badge variant="soft" tone={item.is_active ? 'green' : 'muted'}>
                    {item.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>

                <dl className="mt-4 grid grid-cols-2 gap-x-3 gap-y-3 border-t border-[#F0EEE8] pt-3 text-sm">
                  <div>
                    <dt className="text-[10px] font-medium uppercase tracking-[.05em] text-[#8A8A84]">
                      Role
                    </dt>
                    <dd className="mt-1">
                      <Badge variant="soft" tone={roleTone(item.role)}>
                        {roleLabel(item.role)}
                      </Badge>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[10px] font-medium uppercase tracking-[.05em] text-[#8A8A84]">
                      Contact
                    </dt>
                    <dd className="mt-1 text-[13px] text-[#5C5C56]">{managedUserContact(item)}</dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-[10px] font-medium uppercase tracking-[.05em] text-[#8A8A84]">
                      Franchise
                    </dt>
                    <dd className="mt-1 text-[13px] text-[#4A4A46]">{managedUserFranchiseLabel(item)}</dd>
                  </div>
                </dl>

                <div className="mt-4 flex items-center gap-1.5 border-t border-[#F0EEE8] pt-3">
                  <ActionButton variant="outline" onClick={() => setEditTarget(item)}>
                    Edit
                  </ActionButton>
                  {moreMenu(item)}
                </div>
              </AdminListCard>
            ))}
          </div>
        </>
      ) : null}

      {showAdd ? (
        <Modal
          title="Add User"
          onClose={() => {
            setShowAdd(false);
            setCreateError(null);
            setCreateFieldErrors({});
          }}
        >
          <UserForm
            mode="create"
            initial={createInitial}
            franchises={franchises}
            submitting={createMutation.isPending}
            formError={createError}
            apiFieldErrors={createFieldErrors}
            onCancel={() => {
              setShowAdd(false);
              setCreateError(null);
              setCreateFieldErrors({});
            }}
            onClearSubmitError={() => {
              setCreateError(null);
              setCreateFieldErrors({});
            }}
            onSubmit={(values) => {
              setCreateError(null);
              setCreateFieldErrors({});
              createMutation.mutate(values);
            }}
          />
        </Modal>
      ) : null}

      {viewTarget ? (
        <Modal title="User details" onClose={() => setViewTarget(null)}>
          <UserDetail user={viewTarget} />
        </Modal>
      ) : null}

      {editTarget ? (
        <Modal title="Edit user" onClose={() => setEditTarget(null)}>
          <UserForm
            mode="edit"
            initial={userToForm(editTarget)}
            franchises={franchises}
            submitting={updateMutation.isPending}
            onCancel={() => setEditTarget(null)}
            onSubmit={(values) => updateMutation.mutate({ id: editTarget.id, values })}
          />
        </Modal>
      ) : null}

      {statusTarget ? (
        <Modal
          title={statusTarget.is_active ? 'Deactivate user' : 'Activate user'}
          onClose={() => setStatusTarget(null)}
        >
          <p className="mb-4 text-sm text-[#4A4A46]">
            {statusTarget.is_active
              ? `Deactivate ${statusTarget.full_name}? They will not be able to access the application. The account is preserved.`
              : `Activate ${statusTarget.full_name}?`}
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={() => setStatusTarget(null)}>
              Cancel
            </Button>
            <Button
              variant={statusTarget.is_active ? 'danger' : 'primary'}
              disabled={statusMutation.isPending}
              onClick={() =>
                statusMutation.mutate({
                  id: statusTarget.id,
                  is_active: !statusTarget.is_active,
                })
              }
            >
              {statusMutation.isPending
                ? 'Updating…'
                : statusTarget.is_active
                  ? 'Deactivate'
                  : 'Activate'}
            </Button>
          </div>
        </Modal>
      ) : null}

      {resetTarget ? (
        <Modal title="Reset password" onClose={() => setResetTarget(null)}>
          <p className="mb-4 text-sm text-[#4A4A46]">
            Send a password recovery email to <strong>{resetTarget.email ?? resetTarget.full_name}</strong>?
            A new password will not be displayed.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={() => setResetTarget(null)}>
              Cancel
            </Button>
            <Button
              disabled={resetMutation.isPending}
              onClick={() => resetMutation.mutate(resetTarget.id)}
            >
              {resetMutation.isPending ? 'Sending…' : 'Send reset'}
            </Button>
          </div>
        </Modal>
      ) : null}

      {deleteTarget ? (
        <Modal
          title={DELETE_USER_TITLE}
          onClose={() => {
            setDeleteTarget(null);
            setDeleteError(null);
          }}
        >
          <p className="text-sm text-[#1A1A18]">{DELETE_USER_CONFIRM_MESSAGE}</p>
          <p className="mt-1 text-sm font-medium text-[#5C5C56]">{deleteTarget.full_name}</p>
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
