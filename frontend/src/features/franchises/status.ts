import type { FranchiseStatus } from '../../types/franchise';

export function statusTone(
  status: FranchiseStatus,
): 'green' | 'orange' | 'navy' | 'muted' | 'red' | 'amber' {
  switch (status) {
    case 'ACTIVE':
      return 'green';
    case 'SETUP':
      return 'navy';
    case 'PENDING_PAYMENT':
      return 'orange';
    case 'APPLICATION':
      return 'amber';
    case 'SUSPENDED':
      return 'red';
    case 'CLOSED':
    default:
      return 'muted';
  }
}

export function statusLabel(status: FranchiseStatus): string {
  return status.replaceAll('_', ' ');
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function apiErrorMessage(error: unknown, fallback: string): string {
  if (
    error &&
    typeof error === 'object' &&
    'response' in error &&
    error.response &&
    typeof error.response === 'object' &&
    'data' in error.response
  ) {
    const data = (error.response as { data?: { detail?: unknown } }).data;
    const detail = data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (item && typeof item === 'object' && 'msg' in item) {
            return String((item as { msg: string }).msg);
          }
          return String(item);
        })
        .join('; ');
    }
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}
