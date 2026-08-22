export const EMPLOYEE_ACTIVITY_LOAD_ERROR =
  'Unable to load employee activity. Please try again.';

export type EmployeeSessionStatus = 'ACTIVE' | 'COMPLETED';

export type EmployeeSession = {
  id: string;
  employee_id: string;
  employee_name_snapshot: string;
  login_at: string;
  logout_at: string | null;
  status: EmployeeSessionStatus;
  created_at?: string | null;
};

export function isActiveSession(session: Pick<EmployeeSession, 'status' | 'logout_at'>): boolean {
  return session.status === 'ACTIVE' || !session.logout_at;
}

export function formatActivityDate(value: string | null | undefined): string {
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '—';
  return parsed.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function formatActivityTime(value: string | null | undefined): string {
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '—';
  return parsed.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

export function logoutDisplay(session: Pick<EmployeeSession, 'status' | 'logout_at'>): string {
  if (isActiveSession(session)) return 'Currently Logged In';
  return formatActivityTime(session.logout_at);
}

export function sessionStatusLabel(session: Pick<EmployeeSession, 'status' | 'logout_at'>): string {
  return isActiveSession(session) ? 'Logged In' : 'Completed';
}

export function toEmployeeActivityError(_error: unknown): string {
  return EMPLOYEE_ACTIVITY_LOAD_ERROR;
}
