import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { APP_DOCUMENT_NAME, documentTitleForRole } from '../src/components/seo/documentTitle.ts';

describe('documentTitleForRole', () => {
  it('maps SYSTEM_ADMIN to Admin | RealStick', () => {
    assert.equal(documentTitleForRole('SYSTEM_ADMIN'), 'Admin | RealStick');
  });

  it('maps FRANCHISE_OWNER to Owner | RealStick', () => {
    assert.equal(documentTitleForRole('FRANCHISE_OWNER'), 'Owner | RealStick');
  });

  it('maps EMPLOYEE to Staff | RealStick', () => {
    assert.equal(documentTitleForRole('EMPLOYEE'), 'Staff | RealStick');
  });

  it('returns null for unauthenticated and unknown roles', () => {
    assert.equal(documentTitleForRole(null), null);
    assert.equal(documentTitleForRole(undefined), null);
  });

  it('preserves the RealStick application name', () => {
    assert.equal(APP_DOCUMENT_NAME, 'RealStick');
    assert.ok(documentTitleForRole('SYSTEM_ADMIN')?.endsWith(`| ${APP_DOCUMENT_NAME}`));
    assert.ok(documentTitleForRole('FRANCHISE_OWNER')?.endsWith(`| ${APP_DOCUMENT_NAME}`));
    assert.ok(documentTitleForRole('EMPLOYEE')?.endsWith(`| ${APP_DOCUMENT_NAME}`));
  });
});
