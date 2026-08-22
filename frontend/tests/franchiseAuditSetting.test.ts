import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import { canAccessAudit, navForRole } from '../src/features/auth/nav.ts';
import {
  FRANCHISE_AUDIT_SETTING_COPY,
  franchiseAuditSettingStateLabel,
  resolveFranchiseAuditToggle,
} from '../src/features/franchises/franchiseAuditSetting.ts';

const root = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(root, '..');
const franchisesPage = readFileSync(
  join(frontendRoot, 'src/features/franchises/FranchisesPage.tsx'),
  'utf8',
);
const auditSettings = readFileSync(
  join(frontendRoot, 'src/features/franchises/FranchiseAuditSettings.tsx'),
  'utf8',
);
const appTsx = readFileSync(join(frontendRoot, 'src/app/App.tsx'), 'utf8');
const auditRoute = readFileSync(
  join(frontendRoot, 'src/components/routing/AuditProtectedRoute.tsx'),
  'utf8',
);
const appShell = readFileSync(join(frontendRoot, 'src/components/layout/AppShell.tsx'), 'utf8');
const navTs = readFileSync(join(frontendRoot, 'src/features/auth/nav.ts'), 'utf8');

function labelsFor(role: 'SYSTEM_ADMIN' | 'FRANCHISE_OWNER' | 'EMPLOYEE', enabled?: boolean) {
  return navForRole(role, enabled === undefined ? undefined : { franchiseOwnerAuditEnabled: enabled }).map(
    (item) => item.label,
  );
}

describe('Admin Franchise Audit setting UI', () => {
  it('shows the Audit visibility setting on Franchise Management', () => {
    assert.equal(franchisesPage.includes('FranchiseAuditSettings'), true);
    assert.equal(FRANCHISE_AUDIT_SETTING_COPY.heading, 'Franchise Audit');
    assert.equal(FRANCHISE_AUDIT_SETTING_COPY.label, 'Allow Franchise Owners to access Audit');
    assert.equal(
      FRANCHISE_AUDIT_SETTING_COPY.description,
      'Controls whether the Audit feature is available to Franchise Owners.',
    );
    assert.equal(auditSettings.includes('FRANCHISE_AUDIT_SETTING_COPY.heading'), true);
    assert.equal(auditSettings.includes('FRANCHISE_AUDIT_SETTING_COPY.label'), true);
    assert.equal(auditSettings.includes('FRANCHISE_AUDIT_SETTING_COPY.description'), true);
    assert.equal(auditSettings.includes('type="checkbox"'), true);
    assert.equal(auditSettings.includes('franchiseAuditSettingStateLabel'), true);
    assert.equal(auditSettings.includes('?? false'), true);
    assert.equal(franchiseAuditSettingStateLabel(false), 'Off');
  });

  it('lets Admin enable the setting', () => {
    const result = resolveFranchiseAuditToggle(false, true, true);
    assert.equal(result.value, true);
    assert.equal(result.error, null);
    assert.equal(result.feedback, FRANCHISE_AUDIT_SETTING_COPY.saveSuccess);
    assert.equal(franchiseAuditSettingStateLabel(true), 'On');
  });

  it('lets Admin disable the setting', () => {
    const result = resolveFranchiseAuditToggle(true, false, true);
    assert.equal(result.value, false);
    assert.equal(result.error, null);
    assert.equal(result.feedback, FRANCHISE_AUDIT_SETTING_COPY.saveSuccess);
    assert.equal(franchiseAuditSettingStateLabel(false), 'Off');
  });

  it('keeps the previous value and a safe error when saving fails', () => {
    const result = resolveFranchiseAuditToggle(true, false, false);
    assert.equal(result.value, true);
    assert.equal(result.feedback, null);
    assert.equal(result.error, FRANCHISE_AUDIT_SETTING_COPY.saveError);
    assert.equal(result.error.includes('status code'), false);
    assert.equal(result.error.toLowerCase().includes('sql'), false);
    assert.equal(result.error.toLowerCase().includes('stack'), false);
    assert.equal(auditSettings.includes('apiErrorMessage'), false);
    assert.equal(auditSettings.includes('disabled={saveMutation.isPending}'), true);
  });
});

describe('Franchise Audit navigation and route protection', () => {
  it('shows Audit to Franchise Owners when the setting is enabled', () => {
    assert.equal(labelsFor('FRANCHISE_OWNER', true).includes('Audit'), true);
    assert.equal(canAccessAudit('FRANCHISE_OWNER', true), true);
    assert.equal(
      navForRole('FRANCHISE_OWNER', { franchiseOwnerAuditEnabled: true }).some(
        (item) => item.path === '/audit',
      ),
      true,
    );
  });

  it('defaults Franchise Owner Audit to disabled when the setting is missing', () => {
    assert.equal(labelsFor('FRANCHISE_OWNER').includes('Audit'), false);
    assert.equal(canAccessAudit('FRANCHISE_OWNER', undefined), false);
    assert.equal(canAccessAudit('FRANCHISE_OWNER', null), false);
    assert.equal(navForRole('FRANCHISE_OWNER').some((item) => item.path === '/audit'), false);
  });

  it('hides Audit from Franchise Owners when the setting is disabled', () => {
    assert.equal(labelsFor('FRANCHISE_OWNER', false).includes('Audit'), false);
    assert.equal(canAccessAudit('FRANCHISE_OWNER', false), false);
    assert.equal(
      navForRole('FRANCHISE_OWNER', { franchiseOwnerAuditEnabled: false }).some(
        (item) => item.path === '/audit',
      ),
      false,
    );
  });

  it('blocks Franchise Owner direct navigation to /audit when disabled', () => {
    assert.equal(appTsx.includes('AuditProtectedRoute'), true);
    assert.equal(appTsx.includes('path="audit"'), true);
    assert.equal(auditRoute.includes('canAccessAudit'), true);
    assert.equal(auditRoute.includes('staffLandingPath'), true);
    assert.equal(auditRoute.includes("Navigate to={staffLandingPath(profile.role)}"), true);
    assert.equal(auditRoute.includes('AuditsPage'), false);
    assert.equal(canAccessAudit('FRANCHISE_OWNER', false), false);
  });

  it('shows Audit to SYSTEM_ADMIN regardless of the setting', () => {
    assert.equal(labelsFor('SYSTEM_ADMIN', false).includes('Audit'), true);
    assert.equal(labelsFor('SYSTEM_ADMIN', true).includes('Audit'), true);
    assert.equal(canAccessAudit('SYSTEM_ADMIN', false), true);
    assert.equal(canAccessAudit('SYSTEM_ADMIN', true), true);
  });

  it('hides Audit from employees', () => {
    assert.equal(labelsFor('EMPLOYEE', true).includes('Audit'), false);
    assert.equal(labelsFor('EMPLOYEE', false).includes('Audit'), false);
    assert.equal(canAccessAudit('EMPLOYEE', true), false);
    assert.equal(navForRole('EMPLOYEE').some((item) => item.path === '/audit'), false);
  });

  it('keeps existing Audit navigation when the setting is enabled', () => {
    const admin = navForRole('SYSTEM_ADMIN');
    const owner = navForRole('FRANCHISE_OWNER', { franchiseOwnerAuditEnabled: true });
    assert.equal(admin.filter((item) => item.label === 'Audit').length, 1);
    assert.equal(owner.filter((item) => item.label === 'Audit').length, 1);
    assert.equal(admin.find((item) => item.label === 'Audit')?.path, '/audit');
    assert.equal(owner.find((item) => item.label === 'Audit')?.path, '/audit');
    assert.equal(appShell.includes('franchiseOwnerAuditEnabled'), true);
    assert.equal(navTs.includes("export const AUDIT_ACCESS_ROLES"), true);
    assert.match(navTs, /AUDIT_ACCESS_ROLES: UserRole\[\] = \['SYSTEM_ADMIN', 'FRANCHISE_OWNER'\]/);
  });
});
