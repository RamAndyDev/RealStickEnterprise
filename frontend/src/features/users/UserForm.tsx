import { useState, type FormEvent } from 'react';

import { Button, ErrorBanner, Field, SelectField } from '../../components/ui';
import type { UserRole } from '../../types/auth';
import type { Franchise } from '../../types/franchise';
import type { ManagedUser } from '../../types/user';
import { validateOwnerForm, type OwnerCreateFieldErrors } from './ownerForm';

export type UserFormValues = {
  full_name: string;
  email: string;
  login_id: string;
  password: string;
  confirm_password: string;
  phone: string;
  role: UserRole;
  franchise_id: string;
};

export function emptyUserForm(role: UserRole = 'SYSTEM_ADMIN'): UserFormValues {
  return {
    full_name: '',
    email: '',
    login_id: '',
    password: '',
    confirm_password: '',
    phone: '',
    role,
    franchise_id: '',
  };
}

export function userToForm(user: ManagedUser): UserFormValues {
  return {
    full_name: user.full_name,
    email: user.email ?? '',
    login_id: user.login_id ?? '',
    password: '',
    confirm_password: '',
    phone: user.phone ?? '',
    role: user.role,
    franchise_id: user.franchise_id ?? '',
  };
}

export function UserForm({
  mode,
  initial,
  franchises = [],
  franchiseLabel,
  submitting,
  employeeMode = false,
  formError = null,
  apiFieldErrors,
  onCancel,
  onSubmit,
  onClearSubmitError,
}: {
  mode: 'create' | 'edit';
  initial: UserFormValues;
  franchises?: Franchise[];
  franchiseLabel?: string;
  submitting: boolean;
  employeeMode?: boolean;
  formError?: string | null;
  apiFieldErrors?: OwnerCreateFieldErrors;
  onCancel: () => void;
  onSubmit: (values: UserFormValues) => void;
  onClearSubmitError?: () => void;
}) {
  const [values, setValues] = useState(initial);
  const [fieldErrors, setFieldErrors] = useState<OwnerCreateFieldErrors>({});
  const isSystemAdmin = values.role === 'SYSTEM_ADMIN';
  const showFranchiseSelect = !franchiseLabel && !isSystemAdmin;
  const showReadOnlyFranchise = Boolean(franchiseLabel);
  const passwordMismatch =
    employeeMode && mode === 'create' && values.password !== values.confirm_password;
  const ownerCreateMode = mode === 'create' && !employeeMode;

  function update<K extends keyof UserFormValues>(key: K, value: UserFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
    if (key === 'full_name') {
      setFieldErrors((current) => (current.full_name ? { ...current, full_name: undefined } : current));
    } else if (key === 'email') {
      setFieldErrors((current) => (current.email ? { ...current, email: undefined } : current));
    } else if (key === 'phone') {
      setFieldErrors((current) => (current.phone ? { ...current, phone: undefined } : current));
    } else if (key === 'franchise_id' || key === 'role') {
      setFieldErrors((current) =>
        current.franchise_id ? { ...current, franchise_id: undefined } : current,
      );
    }
    if (formError || apiFieldErrors?.full_name || apiFieldErrors?.email || apiFieldErrors?.franchise_id) {
      onClearSubmitError?.();
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (ownerCreateMode) {
      const errors = validateOwnerForm(values);
      setFieldErrors(errors);
      if (Object.keys(errors).length > 0) return;
    } else {
      const errors = validateOwnerForm({
        ...values,
        email: values.email || 'placeholder@example.com',
      });
      const next: OwnerCreateFieldErrors = {};
      if (errors.full_name) next.full_name = errors.full_name;
      if (errors.phone) next.phone = errors.phone;
      setFieldErrors(next);
      if (Object.keys(next).length > 0) return;
    }
    onSubmit(values);
  }

  const emailError = fieldErrors.email || apiFieldErrors?.email;
  const nameError = fieldErrors.full_name || apiFieldErrors?.full_name;
  const phoneError = fieldErrors.phone || apiFieldErrors?.phone;
  const franchiseError = fieldErrors.franchise_id || apiFieldErrors?.franchise_id;

  return (
    <form onSubmit={handleSubmit} noValidate={ownerCreateMode}>
      {formError ? (
        <div className="mb-3">
          <ErrorBanner message={formError} />
        </div>
      ) : null}
      {employeeMode && mode === 'create' ? (
        <Field
          label="User ID"
          required
          value={values.login_id}
          onChange={(event) => update('login_id', event.target.value)}
          placeholder="EMP001"
        />
      ) : null}
      <Field
        label="Name"
        required
        value={values.full_name}
        error={nameError}
        onChange={(event) => update('full_name', event.target.value)}
      />
      {employeeMode && mode === 'edit' ? (
        <Field
          label="User ID"
          required
          value={values.login_id}
          onChange={(event) => update('login_id', event.target.value)}
          placeholder="EMP001"
        />
      ) : null}
      {!employeeMode ? (
        <Field
          label="Email"
          type="email"
          required
          value={values.email}
          disabled={mode === 'edit'}
          error={emailError}
          onChange={(event) => update('email', event.target.value)}
        />
      ) : null}
      {employeeMode && mode === 'create' ? (
        <>
          <Field
            label="Initial password"
            type="password"
            required
            autoComplete="new-password"
            value={values.password}
            onChange={(event) => update('password', event.target.value)}
          />
          <Field
            label="Confirm password"
            type="password"
            required
            autoComplete="new-password"
            value={values.confirm_password}
            onChange={(event) => update('confirm_password', event.target.value)}
          />
          {passwordMismatch ? (
            <p className="mb-3 text-xs text-red-600">Passwords do not match.</p>
          ) : null}
        </>
      ) : null}
      <Field
        label="Phone"
        value={values.phone}
        error={phoneError}
        placeholder="+919876543210"
        onChange={(event) => update('phone', event.target.value)}
      />

      {mode === 'create' && !franchiseLabel && !employeeMode ? (
        <SelectField
          label="Role"
          value={values.role}
          onChange={(event) => update('role', event.target.value as UserRole)}
        >
          <option value="SYSTEM_ADMIN">System Admin</option>
          <option value="FRANCHISE_OWNER">Franchise Owner</option>
        </SelectField>
      ) : null}

      {showReadOnlyFranchise ? (
        <div className="mb-3">
          <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
            Franchise
          </span>
          <div className="rounded-lg border border-[#E0DDD5] bg-[#FDFAF4] px-3 py-2.5 text-sm">
            {franchiseLabel}
          </div>
        </div>
      ) : null}

      {showFranchiseSelect ? (
        <SelectField
          label="Franchise"
          required
          value={values.franchise_id}
          error={franchiseError}
          onChange={(event) => update('franchise_id', event.target.value)}
        >
          <option value="">Select franchise</option>
          {franchises.map((franchise) => (
            <option key={franchise.id} value={franchise.id}>
              {franchise.name}
            </option>
          ))}
        </SelectField>
      ) : null}

      {isSystemAdmin && !employeeMode ? (
        <p className="mb-4 text-xs text-[#8A8A84]">System admins are not assigned to a franchise.</p>
      ) : null}

      {mode === 'create' && !employeeMode ? (
        <p className="mb-4 text-xs text-[#8A8A84]">
          A secure password setup invite is emailed. Passwords are never stored in profiles or shown
          here.
        </p>
      ) : null}
      {mode === 'create' && employeeMode ? (
        <p className="mb-4 text-xs text-[#8A8A84]">
          Share the User ID and password with the employee offline. Passwords are never stored in
          profiles.
        </p>
      ) : null}

      <div className="flex justify-end gap-2">
        <Button variant="muted" type="button" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          type="submit"
          disabled={
            submitting ||
            (!ownerCreateMode &&
              (!values.full_name.trim() ||
                (employeeMode && !values.login_id.trim()) ||
                (employeeMode && mode === 'create' && (values.password.length < 8 || passwordMismatch)) ||
                (!employeeMode && mode === 'create' && !values.email.trim()) ||
                (showFranchiseSelect && !values.franchise_id)))
          }
        >
          {submitting ? 'Saving…' : mode === 'create' ? 'Create' : 'Save'}
        </Button>
      </div>
    </form>
  );
}
