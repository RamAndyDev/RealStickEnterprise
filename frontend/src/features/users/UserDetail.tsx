import { Badge } from '../../components/ui';
import type { ManagedUser } from '../../types/user';
import { formatDate } from '../franchises/status';
import { employeeUserIdLabel, roleLabel, roleTone } from './labels';

export function UserDetail({
  user,
  showFranchise = true,
}: {
  user: ManagedUser;
  showFranchise?: boolean;
}) {
  return (
    <dl className="grid gap-3 text-sm sm:grid-cols-2">
      <div>
        <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Name</dt>
        <dd className="mt-1 font-medium">{user.full_name}</dd>
      </div>
      {user.role === 'EMPLOYEE' ? (
        <div>
          <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">User ID</dt>
          <dd className="mt-1 font-medium">{employeeUserIdLabel(user.login_id)}</dd>
        </div>
      ) : (
        <div>
          <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Email</dt>
          <dd className="mt-1 font-medium">{user.email ?? '—'}</dd>
        </div>
      )}
      <div>
        <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Phone</dt>
        <dd className="mt-1 font-medium">{user.phone ?? '—'}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Role</dt>
        <dd className="mt-1">
          <Badge tone={roleTone(user.role)}>{roleLabel(user.role)}</Badge>
        </dd>
      </div>
      {showFranchise ? (
        <div>
          <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Franchise</dt>
          <dd className="mt-1 font-medium">
            {user.role === 'SYSTEM_ADMIN' ? 'None' : (user.franchise_name ?? '—')}
          </dd>
        </div>
      ) : null}
      <div>
        <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Status</dt>
        <dd className="mt-1">
          <Badge tone={user.is_active ? 'green' : 'muted'}>
            {user.is_active ? 'Active' : 'Inactive'}
          </Badge>
        </dd>
      </div>
      <div>
        <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Created</dt>
        <dd className="mt-1 font-medium">{formatDate(user.created_at)}</dd>
      </div>
    </dl>
  );
}
