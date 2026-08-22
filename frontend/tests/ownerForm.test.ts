import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  OWNER_CREATE_FALLBACK,
  OWNER_EMAIL_EXISTS,
  OWNER_FIELD_ERROR,
  applyOwnerCreateResult,
  classifyOwnerCreateError,
  ownerEmailError,
  validateOwnerForm,
} from '../src/features/users/ownerForm.ts';

const root = dirname(fileURLToPath(import.meta.url));
const usersPage = readFileSync(join(root, '../src/features/users/UsersPage.tsx'), 'utf8');
const userForm = readFileSync(join(root, '../src/features/users/UserForm.tsx'), 'utf8');
const franchisesPage = readFileSync(join(root, '../src/features/franchises/FranchisesPage.tsx'), 'utf8');
const employeesPage = readFileSync(join(root, '../src/features/users/EmployeesPage.tsx'), 'utf8');

const emptyOwner = {
  full_name: '',
  email: '',
  role: 'FRANCHISE_OWNER' as const,
  franchise_id: '',
};

function axiosLikeError(options: {
  status?: number;
  statusText?: string;
  detail?: unknown;
  message?: string;
  code?: string;
  network?: boolean;
}) {
  const error = new Error(
    options.message ??
      (options.status != null ? `Request failed with status code ${options.status}` : 'Error'),
  );
  const response =
    options.network || options.status == null
      ? undefined
      : {
          status: options.status,
          statusText: options.statusText,
          data: options.detail !== undefined ? { detail: options.detail } : {},
        };
  Object.assign(error, {
    isAxiosError: true,
    code: options.code,
    response,
    request: options.network ? {} : response ? {} : undefined,
  });
  return error;
}

describe('owner create field validation', () => {
  it('shows required-field errors for name, email, and franchise', () => {
    const errors = validateOwnerForm(emptyOwner);
    assert.equal(errors.full_name, OWNER_FIELD_ERROR.nameRequired);
    assert.equal(errors.email, OWNER_FIELD_ERROR.emailRequired);
    assert.equal(errors.franchise_id, OWNER_FIELD_ERROR.franchiseRequired);
  });

  it('shows an invalid-email field error', () => {
    assert.equal(ownerEmailError('not-an-email'), OWNER_FIELD_ERROR.emailInvalid);
    assert.equal(ownerEmailError('owner@example.com'), null);
    assert.equal(
      validateOwnerForm({
        ...emptyOwner,
        full_name: 'Asha',
        email: 'owner@',
        franchise_id: 'franchise-1',
      }).email,
      OWNER_FIELD_ERROR.emailInvalid,
    );
  });

  it('does not invent extra franchise validation for system admins', () => {
    const errors = validateOwnerForm({
      full_name: 'Admin',
      email: 'admin@example.com',
      role: 'SYSTEM_ADMIN',
      franchise_id: '',
    });
    assert.equal(errors.franchise_id, undefined);
    assert.equal(Object.keys(errors).length, 0);
  });

  it('uses owner labels when creating from the franchise owner dialog', () => {
    const errors = validateOwnerForm(emptyOwner, { ownerLabels: true, requireFranchise: false });
    assert.equal(errors.full_name, OWNER_FIELD_ERROR.ownerNameRequired);
    assert.equal(errors.email, OWNER_FIELD_ERROR.ownerEmailRequired);
    assert.equal(errors.franchise_id, undefined);
  });
});

describe('owner create API error mapping', () => {
  it('maps backend field validation into field errors', () => {
    const classified = classifyOwnerCreateError(
      axiosLikeError({
        status: 422,
        detail: [
          { loc: ['body', 'email'], msg: 'Value error, Invalid email format' },
          { loc: ['body', 'full_name'], msg: 'Value error, Name is required' },
        ],
      }),
    );
    assert.equal(classified.fieldErrors.email, OWNER_FIELD_ERROR.emailInvalid);
    assert.equal(classified.fieldErrors.full_name, OWNER_FIELD_ERROR.nameRequired);
    assert.equal(classified.formError, null);
  });

  it('maps a safe backend message into the dialog form error', () => {
    const classified = classifyOwnerCreateError(
      axiosLikeError({
        status: 409,
        detail: 'Franchise already has an active owner or profile conflict',
      }),
    );
    assert.equal(classified.fieldErrors.email, undefined);
    assert.equal(
      classified.formError,
      'Franchise already has an active owner or profile conflict.',
    );
  });

  it('maps a duplicate-email backend message onto the email field', () => {
    const classified = classifyOwnerCreateError(
      axiosLikeError({
        status: 409,
        detail: OWNER_EMAIL_EXISTS,
      }),
    );
    assert.equal(classified.fieldErrors.email, OWNER_EMAIL_EXISTS);
    assert.equal(classified.formError, null);
    assert.equal(classified.fieldErrors.email.toLowerCase().includes('assign'), false);
  });

  it('does not suggest assigning an existing owner for a duplicate email', () => {
    const classified = classifyOwnerCreateError(
      axiosLikeError({
        status: 409,
        detail: 'An auth user with this email already exists. Use assign owner instead.',
      }),
    );
    assert.equal(classified.fieldErrors.email, OWNER_EMAIL_EXISTS);
    assert.equal(classified.formError, null);
    assert.equal(/assign/i.test(classified.fieldErrors.email ?? ''), false);
    assert.equal(OWNER_EMAIL_EXISTS, 'Email already exists. Please use a different email address.');
  });

  it('does not expose raw HTTP, Axios, SQL, or URL details', () => {
    const cases = [
      axiosLikeError({
        status: 400,
        statusText: 'Bad Request',
        message: 'Request failed with status code 400',
      }),
      axiosLikeError({
        status: 500,
        detail: 'relation "profiles" does not exist',
      }),
      axiosLikeError({
        status: 500,
        detail: 'JWT signing failed at https://internal.supabase.local/auth/v1',
      }),
      new Error('AxiosError: timeout of 15000ms exceeded'),
      new Error('400 Bad Request'),
    ];
    for (const error of cases) {
      const classified = classifyOwnerCreateError(error);
      const message = classified.formError ?? '';
      assert.equal(message, OWNER_CREATE_FALLBACK, message);
      assert.equal(message.includes('400'), false, message);
      assert.equal(message.toLowerCase().includes('bad request'), false, message);
      assert.equal(message.includes('Axios'), false, message);
      assert.equal(message.includes('profiles'), false, message);
      assert.equal(message.includes('supabase'), false, message);
      assert.equal(message.includes('http'), false, message);
      assert.equal(Object.keys(classified.fieldErrors).length, 0);
    }
  });
});

describe('owner create dialog result', () => {
  it('closes the dialog after a successful create', () => {
    assert.deepEqual(applyOwnerCreateResult(true), { dialogOpen: false, error: null });
  });

  it('keeps the dialog open after validation or API failure', () => {
    assert.deepEqual(applyOwnerCreateResult(false, OWNER_CREATE_FALLBACK), {
      dialogOpen: true,
      error: OWNER_CREATE_FALLBACK,
    });
    assert.deepEqual(applyOwnerCreateResult(false, null), { dialogOpen: true, error: null });
  });
});

describe('Admin User Management owner creation dialog', () => {
  const createMutation = usersPage.slice(
    usersPage.indexOf('const createMutation'),
    usersPage.indexOf('const updateMutation'),
  );
  const addModal = usersPage.slice(usersPage.indexOf('{showAdd ? ('));

  it('shows field and API errors inside the add-user dialog', () => {
    assert.equal(addModal.includes('<Modal'), true);
    assert.equal(addModal.includes('formError={createError}'), true);
    assert.equal(addModal.includes('apiFieldErrors={createFieldErrors}'), true);
    assert.equal(userForm.includes('<ErrorBanner message={formError} />'), true);
    assert.equal(userForm.includes('error={nameError}'), true);
    assert.equal(userForm.includes('error={emailError}'), true);
    assert.equal(userForm.includes('error={franchiseError}'), true);
    assert.equal(userForm.includes('validateOwnerForm(values)'), true);
  });

  it('does not render owner-create errors on the page behind the dialog', () => {
    const errorBlock = createMutation.slice(createMutation.indexOf('onError'));
    assert.equal(errorBlock.includes('setError('), false);
    assert.equal(errorBlock.includes('apiErrorMessage'), false);
    assert.equal(usersPage.includes('{error && !showAdd && !deleteTarget ? ('), true);
    assert.equal(addModal.includes('formError={createError}'), true);
  });

  it('keeps the dialog open after validation or API failure', () => {
    const errorBlock = createMutation.slice(createMutation.indexOf('onError'));
    assert.equal(errorBlock.includes('setShowAdd(false)'), false);
    assert.equal(errorBlock.includes('classifyOwnerCreateError'), true);
    assert.equal(errorBlock.includes('applyOwnerCreateResult(false'), true);
    assert.equal(userForm.includes('if (Object.keys(errors).length > 0) return;'), true);
  });

  it('stops loading after failure so the user can retry', () => {
    assert.equal(addModal.includes('submitting={createMutation.isPending}'), true);
    assert.equal(userForm.includes('disabled={'), true);
    assert.equal(userForm.includes('submitting'), true);
    assert.equal(userForm.includes("{submitting ? 'Saving…' : mode === 'create' ? 'Create' : 'Save'}"), true);
    assert.equal(errorBlockHasClose(createMutation), false);
  });

  it('still closes the dialog and refreshes the list after a successful create', () => {
    const successBlock = createMutation.slice(
      createMutation.indexOf('onSuccess'),
      createMutation.indexOf('onError'),
    );
    assert.equal(successBlock.includes('setShowAdd(false)'), true);
    assert.equal(successBlock.includes('setFeedback(data.message)'), true);
    assert.equal(successBlock.includes("invalidateQueries({ queryKey: ['admin-users'] })"), true);
    assert.equal(createMutation.includes('createAdminUser'), true);
  });

  it('does not change employee creation or activity tracking', () => {
    assert.equal(employeesPage.includes("title=\"Add Employee\""), true);
    assert.equal(employeesPage.includes('employeeMode'), true);
    assert.equal(userForm.includes('Passwords do not match.'), true);
    assert.equal(usersPage.includes('EmployeeActivityDialog'), false);
    assert.equal(usersPage.includes("{ id: 'EMPLOYEE', label: 'Employees' }"), false);
  });
});

describe('Franchise owner creation dialog', () => {
  const createOwnerMutation = franchisesPage.slice(
    franchisesPage.indexOf('const createOwnerMutation'),
    franchisesPage.indexOf('function resetOwnerForm'),
  );
  const ownerModal = franchisesPage.slice(franchisesPage.indexOf('{ownerTarget ? ('));

  it('shows owner-create errors inside the existing owner dialog', () => {
    assert.equal(ownerModal.includes('Create Franchise Owner'), true);
    assert.equal(ownerModal.includes('<ErrorBanner message={ownerFormError} />'), true);
    assert.equal(ownerModal.includes('error={ownerFieldErrors.full_name}'), true);
    assert.equal(ownerModal.includes('error={ownerFieldErrors.email}'), true);
    assert.equal(ownerModal.includes('validateOwnerForm'), true);
  });

  it('keeps the owner dialog open after create failure and closes it after success', () => {
    const successBlock = createOwnerMutation.slice(
      createOwnerMutation.indexOf('onSuccess'),
      createOwnerMutation.indexOf('onError'),
    );
    const errorBlock = createOwnerMutation.slice(createOwnerMutation.indexOf('onError'));
    assert.equal(successBlock.includes('setOwnerTarget(null)'), true);
    assert.equal(successBlock.includes('setFeedback(data.message)'), true);
    assert.equal(errorBlock.includes('setOwnerTarget(null)'), false);
    assert.equal(errorBlock.includes('setError('), false);
    assert.equal(franchisesPage.includes('{error && !ownerTarget && !showAdd && !deleteTarget ? ('), true);
  });

  it('preserves launch progress, offline payment, and payment history UI', () => {
    assert.equal(franchisesPage.includes('LaunchProgressCompact'), true);
    assert.equal(franchisesPage.includes('LaunchProgressDots'), true);
    assert.equal(franchisesPage.includes('RecordOfflinePaymentDialog'), false);
    assert.equal(franchisesPage.includes('PaymentHistorySection'), false);
  });

  it('keeps the franchise owner action labelled Create Owner and has no Assign Existing workflow', () => {
    assert.equal(franchisesPage.includes('Create Owner'), true);
    assert.match(
      franchisesPage,
      /resetOwnerForm\(item\)\}>\s*Create Owner\s*<\/ActionButton>/,
    );
    assert.equal(franchisesPage.includes('Assign Existing'), false);
    assert.equal(franchisesPage.includes('Assign Franchise Owner'), false);
    assert.equal(franchisesPage.includes('ownerMode'), false);
    assert.equal(franchisesPage.includes('assignFranchiseOwner'), false);
  });
});

function errorBlockHasClose(source: string): boolean {
  const errorBlock = source.slice(source.indexOf('onError'));
  return errorBlock.includes('setShowAdd(false)');
}
