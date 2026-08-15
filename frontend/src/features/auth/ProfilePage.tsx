import { Badge } from '../../components/ui';
import { useAuth } from './AuthProvider';
import { formatDate } from '../franchises/status';
import { roleLabel, roleTone } from '../users/labels';

export function ProfilePage() {
  const { profile } = useAuth();

  if (!profile) {
    return null;
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">My Profile</h1>
      <p className="mt-1 text-sm text-[#8A8A84]">Your application profile from RealStick Enterprise.</p>

      <div className="mt-5 rounded-xl border border-[#E0DDD5] bg-white p-6">
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Name</dt>
            <dd className="mt-1 font-medium">{profile.full_name}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Email</dt>
            <dd className="mt-1 font-medium">{profile.email ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Phone</dt>
            <dd className="mt-1 font-medium">{profile.phone ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Role</dt>
            <dd className="mt-1">
              <Badge tone={roleTone(profile.role)}>{roleLabel(profile.role)}</Badge>
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Franchise</dt>
            <dd className="mt-1 font-medium">
              {profile.role === 'SYSTEM_ADMIN'
                ? 'None'
                : (profile.franchise_name ?? profile.franchise_id ?? '—')}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Status</dt>
            <dd className="mt-1">
              <Badge tone={profile.is_active ? 'green' : 'muted'}>
                {profile.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[#8A8A84]">Created</dt>
            <dd className="mt-1 font-medium">{formatDate(profile.created_at)}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
