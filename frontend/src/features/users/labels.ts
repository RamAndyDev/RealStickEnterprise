import type { UserRole } from '../../types/auth';

export function roleLabel(role: UserRole): string {
  switch (role) {
    case 'SYSTEM_ADMIN':
      return 'System Admin';
    case 'FRANCHISE_OWNER':
      return 'Franchise Owner';
    case 'EMPLOYEE':
      return 'Employee';
    default:
      return role;
  }
}

export function roleTone(role: UserRole): 'navy' | 'orange' | 'green' {
  switch (role) {
    case 'SYSTEM_ADMIN':
      return 'navy';
    case 'FRANCHISE_OWNER':
      return 'orange';
    default:
      return 'green';
  }
}
