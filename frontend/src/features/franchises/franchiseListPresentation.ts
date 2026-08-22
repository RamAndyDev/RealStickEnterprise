import type { Franchise } from '../../types/franchise';

export function franchiseLocationLine(franchise: Pick<Franchise, 'city' | 'state'>): string {
  return [franchise.city, franchise.state].filter(Boolean).join(', ');
}

export function franchiseSummaryCounts(items: Pick<Franchise, 'status' | 'owner'>[]): {
  total: number;
  active: number;
  inactive: number;
  unassigned: number;
} {
  return {
    total: items.length,
    active: items.filter((item) => item.status === 'ACTIVE').length,
    inactive: items.filter((item) => item.status !== 'ACTIVE').length,
    unassigned: items.filter((item) => !item.owner).length,
  };
}
