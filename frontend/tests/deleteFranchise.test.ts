import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  DELETE_FRANCHISE_CONFIRM_MESSAGE,
  DELETE_FRANCHISE_FALLBACK,
  DELETE_FRANCHISE_SUCCESS,
  DELETE_FRANCHISE_TITLE,
  applyDeleteFranchiseResult,
} from '../src/features/franchises/deleteFranchise.ts';

const root = dirname(fileURLToPath(import.meta.url));
const franchisesPage = readFileSync(join(root, '../src/features/franchises/FranchisesPage.tsx'), 'utf8');
const franchisesApi = readFileSync(join(root, '../src/lib/franchisesApi.ts'), 'utf8');

describe('franchise delete dialog', () => {
  it('uses the required confirmation copy', () => {
    assert.equal(DELETE_FRANCHISE_TITLE, 'Delete Franchise');
    assert.equal(DELETE_FRANCHISE_CONFIRM_MESSAGE, 'Are you sure you want to delete this franchise?');
    assert.equal(DELETE_FRANCHISE_SUCCESS, 'Franchise deleted successfully.');
    assert.equal(franchisesPage.includes('title={DELETE_FRANCHISE_TITLE}'), true);
    assert.equal(franchisesPage.includes('{DELETE_FRANCHISE_CONFIRM_MESSAGE}'), true);
    assert.equal(franchisesPage.includes('alert('), false);
    assert.equal(franchisesPage.includes('window.confirm'), false);
  });

  it('keeps the dialog open with a safe business error after failure', () => {
    assert.deepEqual(applyDeleteFranchiseResult(true), { dialogOpen: false, error: null });
    assert.deepEqual(applyDeleteFranchiseResult(false, 'Blocked.'), {
      dialogOpen: true,
      error: 'Blocked.',
    });
    assert.deepEqual(applyDeleteFranchiseResult(false), {
      dialogOpen: true,
      error: DELETE_FRANCHISE_FALLBACK,
    });
    const errorBlock = franchisesPage.slice(franchisesPage.indexOf('const deleteMutation'));
    assert.equal(errorBlock.includes('setDeleteTarget(null)'), true);
    assert.equal(errorBlock.includes('safeApiErrorMessage'), true);
    assert.equal(franchisesPage.includes('<ErrorBanner message={deleteError} />'), true);
  });
});

describe('franchise delete API client', () => {
  it('calls the admin franchise delete endpoint', () => {
    assert.equal(franchisesApi.includes('export async function deleteFranchise'), true);
    assert.equal(franchisesApi.includes('api.delete(`/admin/franchises/${id}`)'), true);
  });
});
