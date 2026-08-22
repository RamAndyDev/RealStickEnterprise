import type { UserRole } from '../../types/auth';

export function managedUserFranchiseLabel(user: {
  role: UserRole;
  franchise_name: string | null;
}): string {
  if (user.role === 'SYSTEM_ADMIN') return 'System Administration';
  const name = user.franchise_name?.trim();
  return name ? name : '—';
}

export function managedUserContact(user: { phone: string | null }): string {
  const phone = user.phone?.trim();
  return phone ? phone : '—';
}
