import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const franchisesPage = readFileSync(join(root, '../src/features/franchises/FranchisesPage.tsx'), 'utf8');

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

  it('keeps primary and secondary actions available', () => {
    assert.equal(franchisesPage.includes('setEditTarget(item)'), true);
    assert.equal(franchisesPage.includes("item.status === 'ACTIVE' ? 'Deactivate…' : 'Activate…'"), true);
    assert.equal(franchisesPage.includes('Create Owner'), true);
    assert.equal(franchisesPage.includes('resetOwnerForm(item)'), true);
    assert.equal(franchisesPage.includes('setDeleteTarget(item)'), true);
    assert.equal(franchisesPage.includes('setDeleteTarget(item)'), true);
    assert.equal(franchisesPage.includes('<ActionMenu>'), true);
    assert.equal(franchisesPage.includes('Assign Existing'), false);
    assert.equal(franchisesPage.includes('assignFranchiseOwner'), false);
  });

  it('uses a mobile card layout without dropping actions', () => {
    assert.equal(franchisesPage.includes('hidden overflow-x-auto'), true);
    assert.equal(franchisesPage.includes('md:block'), true);
    assert.equal(franchisesPage.includes('md:hidden'), true);
    const cards = franchisesPage.slice(franchisesPage.indexOf('grid gap-3 md:hidden'));
    assert.equal(cards.includes('Create Owner'), true);
    assert.equal(cards.includes('Delete'), true);
    assert.equal(cards.includes('Edit'), true);
    assert.equal(cards.includes('LaunchProgressDots'), true);
  });
});
