import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

import {
  ActionButton,
  ActionsTd,
  ActionsTh,
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  LoadingBlock,
  Modal,
  SuccessBanner,
} from '../../components/ui';
import { listFranchises } from '../../lib/franchisesApi';
import {
  createAdminUser,
  listAdminUsers,
  resetAdminUserPassword,
  updateAdminUser,
} from '../../lib/usersApi';
import type { UserRole } from '../../types/auth';
import type { ManagedUser } from '../../types/user';
import { apiErrorMessage, formatDate } from '../franchises/status';
import { roleLabel, roleTone } from './labels';
import { UserDetail } from './UserDetail';
import { UserForm, emptyUserForm, userToForm, type UserFormValues } from './UserForm';

const ROLE_TABS: { id: '' | UserRole; label: string }[] = [
  { id: '', label: 'All' },
  { id: 'SYSTEM_ADMIN', label: 'System Admins' },
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
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
      setShowAdd(false);
      setFeedback(data.message);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to create user.')),
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
  const createInitial = useMemo(() => emptyUserForm(roleFilter || 'SYSTEM_ADMIN'), [roleFilter]);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">User Management</h1>
          <p className="text-xs text-[#8A8A84]">
            {listQuery.isLoading ? 'Loading…' : `${listQuery.data?.total ?? 0} users`}
          </p>
        </div>
        <Button onClick={() => setShowAdd(true)}>+ Add User</Button>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {ROLE_TABS.map((tab) => (
          <button
            key={tab.id || 'all'}
            type="button"
            onClick={() => setRoleFilter(tab.id)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
              roleFilter === tab.id
                ? 'bg-[#0D4F2E] text-white'
                : 'bg-white text-[#4A4A46] ring-1 ring-[#E0DDD5]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search by name, email, phone, or franchise"
        className="mb-4 w-full rounded-lg border border-[#E0DDD5] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1A7A4A]"
      />

      {feedback ? (
        <div className="mb-3">
          <SuccessBanner message={feedback} />
        </div>
      ) : null}
      {error ? (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      ) : null}

      {listQuery.isLoading ? <LoadingBlock label="Loading users…" /> : null}
      {listQuery.isError ? (
        <ErrorBanner message={apiErrorMessage(listQuery.error, 'Unable to load users.')} />
      ) : null}

      {!listQuery.isLoading && !listQuery.isError && items.length === 0 ? (
        <EmptyState title="No users found" hint="Create a user or adjust the current filters." />
      ) : null}

      {!listQuery.isLoading && items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-[#E0DDD5] bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
              <tr>
                <th className="px-4 py-3 font-semibold">Name</th>
                <th className="px-4 py-3 font-semibold">Email</th>
                <th className="px-4 py-3 font-semibold">Role</th>
                <th className="px-4 py-3 font-semibold">Franchise</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Created</th>
                <ActionsTh />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-[#E0DDD5] last:border-b-0">
                  <td className="px-4 py-3 font-semibold">{item.full_name}</td>
                  <td className="px-4 py-3">{item.email ?? '—'}</td>
                  <td className="px-4 py-3">
                    <Badge tone={roleTone(item.role)}>{roleLabel(item.role)}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    {item.role === 'SYSTEM_ADMIN' ? '—' : (item.franchise_name ?? '—')}
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={item.is_active ? 'green' : 'muted'}>
                      {item.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">{formatDate(item.created_at)}</td>
                  <ActionsTd>
                    <ActionButton variant="outline" onClick={() => setViewTarget(item)}>
                      View
                    </ActionButton>
                    <ActionButton variant="outline" onClick={() => setEditTarget(item)}>
                      Edit
                    </ActionButton>
                    <ActionButton
                      fit="status"
                      variant="outline"
                      onClick={() => setStatusTarget(item)}
                    >
                      {item.is_active ? 'Deactivate' : 'Activate'}
                    </ActionButton>
                    <ActionButton fit="lg" variant="muted" onClick={() => setResetTarget(item)}>
                      Reset Password
                    </ActionButton>
                  </ActionsTd>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {showAdd ? (
        <Modal title="Add User" onClose={() => setShowAdd(false)}>
          <UserForm
            mode="create"
            initial={createInitial}
            franchises={franchises}
            submitting={createMutation.isPending}
            onCancel={() => setShowAdd(false)}
            onSubmit={(values) => createMutation.mutate(values)}
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
    </div>
  );
}
