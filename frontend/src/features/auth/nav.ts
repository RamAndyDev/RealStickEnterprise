import type { UserRole } from '../../types/auth';

export type NavItem = {
  label: string;
  path: string;
  roles: UserRole[];
};

/**
 * Role-level Audit eligibility. Franchise Owner visibility is also gated by
 * the persisted Admin setting `franchise_owner_audit_enabled`.
 * SYSTEM_ADMIN always sees Audit. EMPLOYEE never does.
 */
export const AUDIT_ACCESS_ROLES: UserRole[] = ['SYSTEM_ADMIN', 'FRANCHISE_OWNER'];

export type NavVisibilityOptions = {
  franchiseOwnerAuditEnabled?: boolean;
};

/** Role-aware staff navigation. Out-of-scope modules are omitted (inventory, recipes, applications). */
export const APP_NAV: NavItem[] = [
  {
    label: 'Dashboard',
    path: '/dashboard',
    roles: ['SYSTEM_ADMIN', 'FRANCHISE_OWNER'],
  },
  {
    label: 'Franchise Management',
    path: '/franchises',
    roles: ['SYSTEM_ADMIN'],
  },
  {
    label: 'Menu / Products',
    path: '/products',
    roles: ['SYSTEM_ADMIN'],
  },
  {
    label: 'User Management',
    path: '/users',
    roles: ['SYSTEM_ADMIN'],
  },
  {
    label: 'GST Configuration',
    path: '/settings/gst',
    roles: ['SYSTEM_ADMIN'],
  },
  {
    label: 'Promotions',
    path: '/admin/promotions',
    roles: ['SYSTEM_ADMIN'],
  },
  {
    label: 'Employees',
    path: '/employees',
    roles: ['FRANCHISE_OWNER'],
  },
  {
    label: 'Menu / Pricing',
    path: '/owner/menu',
    roles: ['FRANCHISE_OWNER'],
  },
  {
    label: 'Offers & Discounts',
    path: '/owner/offers',
    roles: ['FRANCHISE_OWNER'],
  },
  {
    label: 'Bills',
    path: '/bills',
    roles: ['SYSTEM_ADMIN', 'FRANCHISE_OWNER'],
  },
  {
    label: 'Reports',
    path: '/reports',
    roles: ['SYSTEM_ADMIN', 'FRANCHISE_OWNER'],
  },
  {
    label: 'Gallery Management',
    path: '/admin/gallery',
    roles: ['SYSTEM_ADMIN'],
  },
  {
    label: 'Audit',
    path: '/audit',
    roles: AUDIT_ACCESS_ROLES,
  },
  {
    label: 'Profile',
    path: '/profile',
    roles: ['FRANCHISE_OWNER'],
  },
  {
    label: 'Change Password',
    path: '/change-password',
    roles: ['SYSTEM_ADMIN', 'FRANCHISE_OWNER'],
  },
  {
    label: 'POS',
    path: '/pos',
    roles: ['EMPLOYEE'],
  },
  {
    label: 'Daily Sales',
    path: '/daily-sales',
    roles: ['EMPLOYEE'],
  },
  {
    label: 'Bills',
    path: '/bills',
    roles: ['EMPLOYEE'],
  },
  {
    label: 'My Profile',
    path: '/profile',
    roles: ['EMPLOYEE'],
  },
];

export const PUBLIC_NAV = [
  { label: 'Home', path: '/' },
  { label: 'Menu', path: '/menu' },
  { label: 'About', path: '/about' },
  { label: 'Gallery', path: '/gallery' },
  { label: 'Contact', path: '/contact' },
] as const;

export function canAccessAudit(
  role: UserRole | undefined | null,
  franchiseOwnerAuditEnabled: boolean | null | undefined,
): boolean {
  if (role === 'SYSTEM_ADMIN') return true;
  if (role === 'FRANCHISE_OWNER') return franchiseOwnerAuditEnabled === true;
  return false;
}

export function navForRole(
  role: UserRole | undefined | null,
  options?: NavVisibilityOptions,
): NavItem[] {
  if (!role) return [];
  const ownerAuditEnabled = options?.franchiseOwnerAuditEnabled ?? false;
  return APP_NAV.filter((item) => {
    if (!item.roles.includes(role)) return false;
    if (item.path === '/audit') {
      return canAccessAudit(role, ownerAuditEnabled);
    }
    return true;
  });
}

export function staffLandingPath(role: UserRole | undefined | null): string {
  if (role === 'EMPLOYEE') return '/pos';
  return '/dashboard';
}
