import type { UserRole } from '../../types/auth';

export const APP_DOCUMENT_NAME = 'RealStick';

export function documentTitleForRole(role: UserRole | null | undefined): string | null {
  switch (role) {
    case 'SYSTEM_ADMIN':
      return `Admin | ${APP_DOCUMENT_NAME}`;
    case 'FRANCHISE_OWNER':
      return `Owner | ${APP_DOCUMENT_NAME}`;
    case 'EMPLOYEE':
      return `Staff | ${APP_DOCUMENT_NAME}`;
    default:
      return null;
  }
}
