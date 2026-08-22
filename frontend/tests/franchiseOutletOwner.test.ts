import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  OWNER_EMAIL_EXISTS,
  OWNER_FIELD_ERROR,
  classifyOwnerCreateError,
  validateOwnerForm,
} from '../src/features/users/ownerForm.ts';

const root = dirname(fileURLToPath(import.meta.url));
const franchisesPage = readFileSync(join(root, '../src/features/franchises/FranchisesPage.tsx'), 'utf8');
const outletForm = readFileSync(join(root, '../src/features/franchises/OutletForm.tsx'), 'utf8');
const usersPage = readFileSync(join(root, '../src/features/users/UsersPage.tsx'), 'utf8');

const createMutation = franchisesPage.slice(
  franchisesPage.indexOf('const createMutation'),
  franchisesPage.indexOf('const updateMutation'),
);
const createOwnerMutation = franchisesPage.slice(
  franchisesPage.indexOf('const createOwnerMutation'),
  franchisesPage.indexOf('function resetOwnerForm'),
);
const addModal = franchisesPage.slice(franchisesPage.indexOf('{showAdd ? ('));
const ownerModal = franchisesPage.slice(franchisesPage.indexOf('{ownerTarget ? ('));
const createFields = outletForm.slice(outletForm.indexOf('{isCreate ? ('));

describe('Franchise Management owner action labels', () => {
  it('displays Create Owner for the franchise row action', () => {
    assert.match(
      franchisesPage,
      /resetOwnerForm\(item\)\}>\s*Create Owner\s*<\/ActionButton>/,
    );
    assert.equal(franchisesPage.includes('Create Owner'), true);
  });

  it('does not display Owner as the franchise row action label', () => {
    assert.equal(
      /resetOwnerForm\(item\)\}>\s*Owner\s*<\/ActionButton>/.test(franchisesPage),
      false,
    );
  });

  it('does not display Assign Existing', () => {
    assert.equal(franchisesPage.includes('Assign Existing'), false);
    assert.equal(franchisesPage.includes('Assign Franchise Owner'), false);
    assert.equal(franchisesPage.includes('assignFranchiseOwner'), false);
    assert.equal(ownerModal.includes('Owner Profile ID'), false);
    assert.equal(ownerModal.includes('Assign Owner'), false);
  });
});

describe('Add Outlet owner fields', () => {
  it('makes Owner Name and Owner Phone available in the Add Outlet flow', () => {
    assert.equal(createFields.includes('label="Owner Name"'), true);
    assert.equal(createFields.includes('label="Owner Phone"'), true);
    assert.equal(createFields.includes('label="Owner Email"'), true);
    assert.equal(createFields.includes('creates the outlet and its owner together'), true);
    assert.equal(addModal.includes('mode="create"'), true);
    assert.equal(addModal.includes('<OutletForm'), true);
  });

  it('reuses Observation #12 owner validation for name and email', () => {
    assert.equal(outletForm.includes('validateOwnerForm'), true);
    assert.equal(outletForm.includes('requireOwner: isCreate'), true);
    assert.equal(outletForm.includes('ownerLabels: true'), true);
    assert.equal(outletForm.includes('requireFranchise: false'), true);
    const errors = validateOwnerForm(
      { full_name: '', email: '', role: 'FRANCHISE_OWNER', franchise_id: '' },
      { ownerLabels: true, requireFranchise: false },
    );
    assert.equal(errors.full_name, OWNER_FIELD_ERROR.ownerNameRequired);
    assert.equal(errors.email, OWNER_FIELD_ERROR.ownerEmailRequired);
  });

  it('creates the outlet and owner in one backend operation', () => {
    assert.equal(createMutation.includes('createFranchise(toWritePayload(values, true))'), true);
    assert.equal(createMutation.includes('createFranchiseOwner('), false);
    assert.equal(createMutation.includes('pendingOutletIdRef'), false);
    assert.equal(outletForm.includes('owner_full_name: values.owner_full_name.trim()'), true);
    assert.equal(outletForm.includes('owner_phone: values.owner_phone.trim()'), true);
  });
});

describe('Add Outlet duplicate owner email', () => {
  it('rejects an existing owner email with a message that does not mention assign', () => {
    assert.equal(OWNER_EMAIL_EXISTS, 'Email already exists. Please use a different email address.');
    assert.equal(/assign/i.test(OWNER_EMAIL_EXISTS), false);
    const classified = classifyOwnerCreateError(
      {
        response: {
          status: 409,
          data: { detail: OWNER_EMAIL_EXISTS },
        },
      },
      { ownerLabels: true },
    );
    assert.equal(classified.fieldErrors.email, OWNER_EMAIL_EXISTS);
    assert.equal(classified.formError, null);
    assert.equal(/assign/i.test(classified.fieldErrors.email ?? ''), false);
  });

  it('shows the duplicate-email error inside the Add Outlet dialog and keeps it open', () => {
    const errorBlock = createMutation.slice(createMutation.indexOf('onError'));
    assert.equal(errorBlock.includes('classifyOwnerCreateError'), true);
    assert.equal(errorBlock.includes('setCreateError(result.error)'), true);
    assert.equal(errorBlock.includes('setCreateFieldErrors(classified.fieldErrors)'), true);
    assert.equal(errorBlock.includes('setShowAdd(false)'), false);
    assert.equal(errorBlock.includes('setError('), false);
    assert.equal(addModal.includes('formError={createError}'), true);
    assert.equal(addModal.includes('apiFieldErrors={createFieldErrors}'), true);
    assert.equal(outletForm.includes('error={ownerEmailError}'), true);
    assert.equal(franchisesPage.includes('{error && !ownerTarget && !showAdd ? ('), true);
  });

  it('does not leave a partial outlet to retry against; retry is a fresh single create', () => {
    assert.equal(franchisesPage.includes('pendingOutletIdRef'), false);
    assert.equal(createMutation.includes('createFranchiseOwner('), false);
    const successBlock = createMutation.slice(
      createMutation.indexOf('onSuccess'),
      createMutation.indexOf('onError'),
    );
    assert.equal(successBlock.includes('setShowAdd(false)'), true);
    assert.equal(successBlock.includes("invalidateQueries({ queryKey: ['admin-franchises'] })"), true);
  });
});

describe('Add Outlet dialog error handling', () => {
  it('keeps validation errors inside the Add Outlet dialog', () => {
    assert.equal(outletForm.includes('validateOutletForm(values'), true);
    assert.equal(outletForm.includes('error={ownerNameError}'), true);
    assert.equal(outletForm.includes('error={ownerEmailError}'), true);
    assert.equal(outletForm.includes('if (Object.keys(nextErrors).length) return;'), true);
    assert.equal(addModal.includes('formError={createError}'), true);
    assert.equal(addModal.includes('apiFieldErrors={createFieldErrors}'), true);
  });

  it('keeps API errors inside the Add Outlet dialog', () => {
    const errorBlock = createMutation.slice(createMutation.indexOf('onError'));
    assert.equal(errorBlock.includes('classifyOwnerCreateError'), true);
    assert.equal(errorBlock.includes('setCreateError(result.error)'), true);
    assert.equal(errorBlock.includes('setCreateFieldErrors(classified.fieldErrors)'), true);
    assert.equal(errorBlock.includes('setError('), false);
    assert.equal(errorBlock.includes('setShowAdd(false)'), false);
    assert.equal(outletForm.includes('<ErrorBanner message={formError} />'), true);
    assert.equal(franchisesPage.includes('{error && !ownerTarget && !showAdd ? ('), true);
  });

  it('closes the dialog and refreshes the franchise list after a successful create', () => {
    const successBlock = createMutation.slice(
      createMutation.indexOf('onSuccess'),
      createMutation.indexOf('onError'),
    );
    assert.equal(successBlock.includes('setShowAdd(false)'), true);
    assert.equal(successBlock.includes("invalidateQueries({ queryKey: ['admin-franchises'] })"), true);
    assert.equal(successBlock.includes('applyOwnerCreateResult(true)'), true);
  });
});

describe('Observation #12 franchise owner dialog remains intact', () => {
  it('still validates and reports owner-create errors inside the owner dialog', () => {
    assert.equal(ownerModal.includes('Create Franchise Owner'), true);
    assert.equal(ownerModal.includes('<ErrorBanner message={ownerFormError} />'), true);
    assert.equal(ownerModal.includes('error={ownerFieldErrors.full_name}'), true);
    assert.equal(ownerModal.includes('error={ownerFieldErrors.email}'), true);
    assert.equal(ownerModal.includes('validateOwnerForm'), true);
    assert.equal(ownerModal.includes("{ ownerLabels: true, requireFranchise: false }"), true);
  });

  it('still closes after success and stays open after failure', () => {
    const successBlock = createOwnerMutation.slice(
      createOwnerMutation.indexOf('onSuccess'),
      createOwnerMutation.indexOf('onError'),
    );
    const errorBlock = createOwnerMutation.slice(createOwnerMutation.indexOf('onError'));
    assert.equal(successBlock.includes('setOwnerTarget(null)'), true);
    assert.equal(successBlock.includes('setFeedback(data.message)'), true);
    assert.equal(successBlock.includes("invalidateQueries({ queryKey: ['admin-franchises'] })"), true);
    assert.equal(errorBlock.includes('setOwnerTarget(null)'), false);
    assert.equal(errorBlock.includes('setError('), false);
  });

  it('does not change User Management owner creation', () => {
    assert.equal(usersPage.includes('createAdminUser'), true);
    assert.equal(usersPage.includes('formError={createError}'), true);
    assert.equal(usersPage.includes('apiFieldErrors={createFieldErrors}'), true);
  });

  it('rejects a duplicate email inside the standalone Create Owner dialog without mentioning assign', () => {
    assert.equal(ownerModal.includes('Assign Existing'), false);
    assert.equal(ownerModal.includes('validateOwnerForm'), true);
    assert.equal(ownerModal.includes('<ErrorBanner message={ownerFormError} />'), true);
    assert.equal(ownerModal.includes('error={ownerFieldErrors.email}'), true);
    const errorBlock = createOwnerMutation.slice(createOwnerMutation.indexOf('onError'));
    assert.equal(errorBlock.includes('classifyOwnerCreateError'), true);
    assert.equal(errorBlock.includes('setOwnerTarget(null)'), false);
    assert.equal(/assign/i.test(OWNER_EMAIL_EXISTS), false);
  });
});
