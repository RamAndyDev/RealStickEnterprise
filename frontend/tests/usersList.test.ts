import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import { initialsFromName } from '../src/components/ui/initials.ts';
import {
  managedUserContact,
  managedUserFranchiseLabel,
} from '../src/features/users/userListPresentation.ts';

const root = dirname(fileURLToPath(import.meta.url));
const usersPage = readFileSync(join(root, '../src/features/users/UsersPage.tsx'), 'utf8');

describe('User Management list redesign', () => {
  it('uses the shared page header, tabs, and compact columns', () => {
    assert.equal(usersPage.includes('User Management'), true);
    assert.equal(usersPage.includes('Manage system administrators and franchise owners.'), true);
    assert.equal(usersPage.includes('+ Add User'), true);
    assert.equal(usersPage.includes('Administrators'), true);
    assert.equal(usersPage.includes('Franchise Owners'), true);
    assert.equal(usersPage.includes('>User<'), true);
    assert.equal(usersPage.includes('>Role<'), true);
    assert.equal(usersPage.includes('>Franchise<'), true);
    assert.equal(usersPage.includes('>Contact<'), true);
    assert.equal(usersPage.includes('>Status<'), true);
    assert.equal(usersPage.includes('<InitialsAvatar'), true);
    assert.equal(usersPage.includes('<SegmentedTabs'), true);
  });

  it('keeps existing user-management actions behind a primary Edit and more menu', () => {
    assert.equal(usersPage.includes('setEditTarget(item)'), true);
    assert.equal(usersPage.includes("item.is_active ? 'Deactivate' : 'Activate'"), true);
    assert.equal(usersPage.includes('Reset Password'), true);
    assert.equal(usersPage.includes('setDeleteTarget(item)'), true);
    assert.equal(usersPage.includes('setViewTarget(item)'), true);
    assert.equal(usersPage.includes('<ActionMenu'), true);
    assert.equal(usersPage.includes('destructive'), true);
    assert.equal(usersPage.includes("{ id: 'EMPLOYEE', label: 'Employees' }"), false);
  });

  it('uses cards on small screens instead of a cramped table', () => {
    assert.equal(usersPage.includes('hidden overflow-x-auto'), true);
    assert.equal(usersPage.includes('lg:block'), true);
    assert.equal(usersPage.includes('lg:hidden'), true);
    const cards = usersPage.slice(usersPage.indexOf('grid gap-3 lg:hidden'));
    assert.equal(cards.includes('moreMenu(item)'), true);
    assert.equal(cards.includes('Edit'), true);
  });

  it('improves empty-state copy without changing create behavior', () => {
    assert.equal(usersPage.includes('No users found'), true);
    assert.equal(usersPage.includes('Try changing your filters or add a new user.'), true);
    assert.equal(usersPage.includes('createAdminUser'), true);
  });
});

describe('user list presentation helpers', () => {
  it('shows system administration for admin users without new backend data', () => {
    assert.equal(
      managedUserFranchiseLabel({ role: 'SYSTEM_ADMIN', franchise_name: null }),
      'System Administration',
    );
    assert.equal(
      managedUserFranchiseLabel({ role: 'FRANCHISE_OWNER', franchise_name: 'Gachibowli' }),
      'Gachibowli',
    );
    assert.equal(managedUserFranchiseLabel({ role: 'FRANCHISE_OWNER', franchise_name: null }), '—');
  });

  it('uses existing phone data for the contact column', () => {
    assert.equal(managedUserContact({ phone: '+919876543210' }), '+919876543210');
    assert.equal(managedUserContact({ phone: '  ' }), '—');
    assert.equal(managedUserContact({ phone: null }), '—');
  });

  it('builds avatar initials from the existing full name', () => {
    assert.equal(initialsFromName('Ramprasad'), 'RA');
    assert.equal(initialsFromName('Ram Prasad'), 'RP');
    assert.equal(initialsFromName('  '), '?');
  });
});
