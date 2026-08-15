import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import {
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  LoadingBlock,
  Modal,
  SuccessBanner,
} from '../../components/ui';
import { useAuth } from '../auth/AuthProvider';
import {
  createEmployee,
  listEmployees,
  resetEmployeePassword,
  updateEmployee,
} from '../../lib/usersApi';
import type { ManagedUser } from '../../types/user';
import { apiErrorMessage, formatDate } from '../franchises/status';
import { UserDetail } from './UserDetail';
import { UserForm, emptyUserForm, userToForm, type UserFormValues } from './UserForm';

export function EmployeesPage() {
  const { profile } = useAuth();
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [viewTarget, setViewTarget] = useState<ManagedUser | null>(null);
  const [editTarget, setEditTarget] = useState<ManagedUser | null>(null);
  const [statusTarget, setStatusTarget] = useState<ManagedUser | null>(null);
  const [resetTarget, setResetTarget] = useState<ManagedUser | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ['owner-employees'],
    queryFn: listEmployees,
  });

  const createMutation = useMutation({
    mutationFn: (values: UserFormValues) =>
      createEmployee({
        full_name: values.full_name.trim(),
        email: values.email.trim(),
        phone: values.phone.trim() || null,
      }),
    onSuccess: async (data) => {
      setShowAdd(false);
      setFeedback(data.message);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['owner-employees'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to create employee.')),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: UserFormValues }) =>
      updateEmployee(id, {
        full_name: values.full_name.trim(),
        phone: values.phone.trim() || null,
      }),
    onSuccess: async () => {
      setEditTarget(null);
      setFeedback('Employee updated.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['owner-employees'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update employee.')),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateEmployee(id, { is_active }),
    onSuccess: async (data) => {
      setStatusTarget(null);
      setFeedback(`${data.full_name} is now ${data.is_active ? 'active' : 'inactive'}.`);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['owner-employees'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update employee status.')),
  });

  const resetMutation = useMutation({
    mutationFn: (id: string) => resetEmployeePassword(id),
    onSuccess: async (data) => {
      setResetTarget(null);
      setFeedback(data.message);
      setError(null);
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to reset password.')),
  });

  const items = listQuery.data?.items ?? [];
  const activeCount = listQuery.data?.active_count ?? 0;
  const limit = listQuery.data?.employee_limit ?? 10;
  const atLimit = activeCount >= limit;
  const franchiseLabel =
    profile?.franchise_name || (profile?.franchise_id ? `Franchise ${profile.franchise_id}` : 'Your franchise');

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">Employees</h1>
          <p className="text-xs text-[#8A8A84]">{franchiseLabel}</p>
        </div>
        <Button onClick={() => setShowAdd(true)} disabled={atLimit} title={atLimit ? 'Active employee limit reached' : undefined}>
          + Add Employee
        </Button>
      </div>

      <div className="mb-4 rounded-xl border border-[#E0DDD5] bg-white p-4">
        <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
          Active employees
        </div>
        <div className="mt-1 font-serif text-3xl font-bold text-[#1A7A4A]">
          {activeCount} / {limit}
        </div>
        {atLimit ? (
          <p className="mt-1 text-xs text-[#8A8A84]">
            Maximum of {limit} active employees reached. Deactivate an employee to add another.
          </p>
        ) : null}
      </div>

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

      {listQuery.isLoading ? <LoadingBlock label="Loading employees…" /> : null}
      {listQuery.isError ? (
        <ErrorBanner message={apiErrorMessage(listQuery.error, 'Unable to load employees.')} />
      ) : null}

      {!listQuery.isLoading && !listQuery.isError && items.length === 0 ? (
        <EmptyState title="No employees yet" hint="Add the first employee for this franchise." />
      ) : null}

      {!listQuery.isLoading && items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-[#E0DDD5] bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
              <tr>
                <th className="px-4 py-3 font-semibold">Name</th>
                <th className="px-4 py-3 font-semibold">Email</th>
                <th className="px-4 py-3 font-semibold">Phone</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Created</th>
                <th className="px-4 py-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-[#E0DDD5] last:border-b-0">
                  <td className="px-4 py-3 font-semibold">{item.full_name}</td>
                  <td className="px-4 py-3">{item.email ?? '—'}</td>
                  <td className="px-4 py-3">{item.phone ?? '—'}</td>
                  <td className="px-4 py-3">
                    <Badge tone={item.is_active ? 'green' : 'muted'}>
                      {item.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">{formatDate(item.created_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={() => setViewTarget(item)}>
                        View
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setEditTarget(item)}>
                        Edit
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setStatusTarget(item)}>
                        {item.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                      <Button size="sm" variant="muted" onClick={() => setResetTarget(item)}>
                        Reset Password
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {showAdd ? (
        <Modal title="Add Employee" onClose={() => setShowAdd(false)}>
          {atLimit ? (
            <p className="text-sm text-[#4A4A46]">
              Maximum of {limit} active employees reached. Deactivate an employee before adding
              another.
            </p>
          ) : (
            <UserForm
              mode="create"
              initial={emptyUserForm('EMPLOYEE')}
              franchiseLabel={franchiseLabel}
              submitting={createMutation.isPending}
              onCancel={() => setShowAdd(false)}
              onSubmit={(values) => createMutation.mutate(values)}
            />
          )}
        </Modal>
      ) : null}

      {viewTarget ? (
        <Modal title="Employee details" onClose={() => setViewTarget(null)}>
          <UserDetail user={viewTarget} />
        </Modal>
      ) : null}

      {editTarget ? (
        <Modal title="Edit employee" onClose={() => setEditTarget(null)}>
          <UserForm
            mode="edit"
            initial={userToForm(editTarget)}
            franchiseLabel={franchiseLabel}
            submitting={updateMutation.isPending}
            onCancel={() => setEditTarget(null)}
            onSubmit={(values) => updateMutation.mutate({ id: editTarget.id, values })}
          />
        </Modal>
      ) : null}

      {statusTarget ? (
        <Modal
          title={statusTarget.is_active ? 'Deactivate employee' : 'Activate employee'}
          onClose={() => setStatusTarget(null)}
        >
          <p className="mb-4 text-sm text-[#4A4A46]">
            {statusTarget.is_active
              ? `Deactivate ${statusTarget.full_name}? They will lose application access. The profile is kept.`
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
            A password will not be displayed.
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
