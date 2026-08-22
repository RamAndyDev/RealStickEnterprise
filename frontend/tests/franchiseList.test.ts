import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import { franchiseLocationLine, franchiseSummaryCounts } from '../src/features/franchises/franchiseListPresentation.ts';
import type { Franchise } from '../src/types/franchise.ts';

const root = dirname(fileURLToPath(import.meta.url));
const franchisesPage = readFileSync(join(root, '../src/features/franchises/FranchisesPage.tsx'), 'utf8');
const uiIndex = readFileSync(join(root, '../src/components/ui/index.tsx'), 'utf8');

function franchise(overrides: Partial<Franchise> = {}): Pick<Franchise, 'status' | 'owner' | 'city' | 'state'> {
  return {
    status: 'ACTIVE',
    owner: { id: '1', full_name: 'Owner', email: 'o@example.com', phone: null, is_active: true },
    city: 'Hyderabad',
    state: 'Telangana',
    ...overrides,
  };
}

describe('Franchise Management list redesign', () => {
  it('keeps the required franchise information visible', () => {
    assert.equal(franchisesPage.includes('>Outlet<'), true);
    assert.equal(franchisesPage.includes('>Owner<'), true);
    assert.equal(franchisesPage.includes('>Contact<'), true);
    assert.equal(franchisesPage.includes('>Status<'), true);
    assert.equal(franchisesPage.includes('>Launch<'), true);
    assert.equal(franchisesPage.includes('>Payment<'), true);
    assert.equal(franchisesPage.includes("item.owner?.full_name ?? 'Unassigned'"), true);
    assert.equal(franchisesPage.includes('<LaunchProgressCompact'), true);
    assert.equal(franchisesPage.includes('<FranchiseAuditSettings'), true);
  });

  it('uses a clean page header and summary cards from existing list data', () => {
    assert.equal(franchisesPage.includes('Franchise Management'), true);
    assert.equal(
      franchisesPage.includes('Manage franchise outlets, owners, launch progress and payments.'),
      true,
    );
    assert.equal(franchisesPage.includes('+ Add Outlet'), true);
    assert.equal(franchisesPage.includes('Total Outlets'), true);
    assert.equal(franchisesPage.includes('Unassigned Owner'), true);
    assert.equal(franchisesPage.includes('franchiseSummaryCounts'), true);
    assert.equal(franchisesPage.includes('/admin/franchises/summary'), false);
  });

  it('keeps primary and secondary actions available', () => {
    assert.equal(franchisesPage.includes('setEditTarget(item)'), true);
    assert.equal(franchisesPage.includes("item.status === 'ACTIVE' ? 'Deactivate…' : 'Activate…'"), true);
    assert.equal(franchisesPage.includes('Create Owner'), true);
    assert.equal(franchisesPage.includes('resetOwnerForm(item)'), true);
    assert.equal(franchisesPage.includes('setDeleteTarget(item)'), true);
    assert.equal(franchisesPage.includes('<ActionMenu'), true);
    assert.equal(franchisesPage.includes('Assign Existing'), false);
    assert.equal(franchisesPage.includes('assignFranchiseOwner'), false);
    assert.match(franchisesPage, /View/);
  });

  it('uses a mobile card layout without dropping actions', () => {
    assert.equal(franchisesPage.includes('hidden overflow-x-auto'), true);
    assert.equal(franchisesPage.includes('lg:block'), true);
    assert.equal(franchisesPage.includes('lg:hidden'), true);
    assert.equal(franchisesPage.includes('Create Owner'), true);
    assert.equal(franchisesPage.includes('Delete'), true);
    assert.equal(franchisesPage.includes('Edit'), true);
    assert.equal(franchisesPage.includes('LaunchProgressCompact'), true);
    const cards = franchisesPage.slice(franchisesPage.indexOf('grid gap-3 lg:hidden'));
    assert.equal(cards.includes('moreMenu(item, true)'), true);
    assert.equal(cards.includes('View'), true);
  });

  it('uses the shared more-actions menu instead of a crowded row of buttons', () => {
    assert.equal(uiIndex.includes('fit="icon"'), true);
    assert.equal(uiIndex.includes('MoreHorizontal'), true);
    assert.equal(uiIndex.includes("event.key === 'Escape'"), true);
    assert.equal(franchisesPage.includes('<ActionMenuSeparator'), true);
  });
});

describe('franchise list presentation helpers', () => {
  it('joins existing city and state without adding new fields', () => {
    assert.equal(franchiseLocationLine(franchise()), 'Hyderabad, Telangana');
    assert.equal(franchiseLocationLine(franchise({ state: null })), 'Hyderabad');
    assert.equal(franchiseLocationLine(franchise({ city: null, state: null })), '');
  });

  it('summarizes loaded franchise rows for KPI cards', () => {
    const counts = franchiseSummaryCounts([
      franchise({ status: 'ACTIVE' }),
      franchise({ status: 'SETUP', owner: null }),
      franchise({ status: 'SUSPENDED', owner: null }),
    ]);
    assert.deepEqual(counts, { total: 3, active: 1, inactive: 2, unassigned: 2 });
  });
});
