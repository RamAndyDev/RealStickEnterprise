import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import { REALSTICK_LOGO_ALT, REALSTICK_LOGO_SRC } from '../src/components/branding/brand.ts';
import { AUDIT_ACCESS_ROLES, navForRole } from '../src/features/auth/nav.ts';

const root = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(root, '..');
const publicLogo = join(frontendRoot, 'public', 'realstick-logo.jpeg');
const publicLayout = readFileSync(join(frontendRoot, 'src/components/layout/PublicLayout.tsx'), 'utf8');
const loginPage = readFileSync(join(frontendRoot, 'src/features/auth/LoginPage.tsx'), 'utf8');
const heroArt = readFileSync(join(frontendRoot, 'src/features/public/HeroArt.tsx'), 'utf8');
const indexHtml = readFileSync(join(frontendRoot, 'index.html'), 'utf8');
const logoComponent = readFileSync(
  join(frontendRoot, 'src/components/branding/RealStickLogo.tsx'),
  'utf8',
);
const franchisesPage = readFileSync(join(frontendRoot, 'src/features/franchises/FranchisesPage.tsx'), 'utf8');
const franchiseDetail = readFileSync(
  join(frontendRoot, 'src/features/franchises/FranchiseDetailPage.tsx'),
  'utf8',
);

describe('RealStick official branding', () => {
  it('serves the supplied logo from the Vite public root', () => {
    assert.equal(REALSTICK_LOGO_SRC, '/realstick-logo.jpeg');
    assert.equal(REALSTICK_LOGO_ALT, 'RealStick');
    assert.equal(existsSync(publicLogo), true);
    const bytes = readFileSync(publicLogo);
    assert.equal(bytes.length > 0, true);
    assert.equal(bytes[0], 0xff);
    assert.equal(bytes[1], 0xd8);
    assert.equal(bytes[2], 0xff);
  });

  it('uses the shared logo component instead of duplicated asset paths', () => {
    assert.equal(logoComponent.includes('REALSTICK_LOGO_SRC'), true);
    assert.equal(logoComponent.includes("alt={alt}"), true);
    assert.equal(publicLayout.includes('RealStickLogo'), true);
    assert.equal(loginPage.includes('RealStickLogo'), true);
    assert.equal(heroArt.includes('RealStickLogo'), true);
    assert.equal(publicLayout.includes('/realstick-logo.jpeg'), false);
    assert.equal(loginPage.includes('/realstick-logo.jpeg'), false);
    assert.equal(heroArt.includes('/realstick-logo.jpeg'), false);
    assert.equal(indexHtml.includes('href="/realstick-logo.jpeg"'), true);
  });
});

describe('Franchise Audit visibility', () => {
  it('keeps Admin and Franchise Owner access, and hides Audit from employees', () => {
    assert.deepEqual(AUDIT_ACCESS_ROLES, ['SYSTEM_ADMIN', 'FRANCHISE_OWNER']);
    const adminLabels = navForRole('SYSTEM_ADMIN').map((item) => item.label);
    const ownerLabels = navForRole('FRANCHISE_OWNER').map((item) => item.label);
    const employeeLabels = navForRole('EMPLOYEE').map((item) => item.label);
    assert.equal(adminLabels.includes('Audit'), true);
    assert.equal(ownerLabels.includes('Audit'), true);
    assert.equal(employeeLabels.includes('Audit'), false);
    assert.equal(
      navForRole('SYSTEM_ADMIN').some((item) => item.path === '/audit'),
      true,
    );
    assert.equal(
      navForRole('FRANCHISE_OWNER').some((item) => item.path === '/audit'),
      true,
    );
  });

  it('is a staff navigation item, not a Franchise Management list/detail action', () => {
    assert.equal(franchisesPage.includes('Audit'), false);
    assert.equal(franchiseDetail.includes('Audit'), false);
    const audit = navForRole('SYSTEM_ADMIN').find((item) => item.label === 'Audit');
    assert.equal(audit?.path, '/audit');
  });
});
