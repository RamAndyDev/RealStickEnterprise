import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  DELETE_USER_CONFIRM_MESSAGE,
  DELETE_USER_FALLBACK,
  DELETE_USER_SUCCESS,
  DELETE_USER_TITLE,
  applyDeleteUserResult,
} from '../src/features/users/deleteUser.ts';

const root = dirname(fileURLToPath(import.meta.url));
const usersPage = readFileSync(join(root, '../src/features/users/UsersPage.tsx'), 'utf8');
const usersApi = readFileSync(join(root, '../src/lib/usersApi.ts'), 'utf8');

describe('user delete dialog', () => {
  it('uses the required confirmation copy', () => {
    assert.equal(DELETE_USER_TITLE, 'Delete User');
    assert.equal(DELETE_USER_CONFIRM_MESSAGE, 'Are you sure you want to delete this user?');
    assert.equal(DELETE_USER_SUCCESS, 'User deleted successfully.');
    assert.equal(usersPage.includes('title={DELETE_USER_TITLE}'), true);
    assert.equal(usersPage.includes('{DELETE_USER_CONFIRM_MESSAGE}'), true);
    assert.equal(usersPage.includes('alert('), false);
    assert.equal(usersPage.includes('window.confirm'), false);
  });

  it('keeps existing user-management actions', () => {
    assert.equal(usersPage.includes('setEditTarget(item)'), true);
    assert.equal(usersPage.includes("item.is_active ? 'Deactivate' : 'Activate'"), true);
    assert.equal(usersPage.includes('Reset Password'), true);
    assert.equal(usersPage.includes('setDeleteTarget(item)'), true);
  });

  it('keeps the dialog open after a failed delete', () => {
    assert.deepEqual(applyDeleteUserResult(false, 'Blocked.'), {
      dialogOpen: true,
      error: 'Blocked.',
    });
    assert.deepEqual(applyDeleteUserResult(false), {
      dialogOpen: true,
      error: DELETE_USER_FALLBACK,
    });
    assert.equal(usersPage.includes('safeApiErrorMessage'), true);
    assert.equal(usersPage.includes('<ErrorBanner message={deleteError} />'), true);
  });
});

describe('user delete API client', () => {
  it('calls the admin user delete endpoint', () => {
    assert.equal(usersApi.includes('export async function deleteAdminUser'), true);
    assert.equal(usersApi.includes('api.delete(`/admin/users/${id}`)'), true);
  });
});
