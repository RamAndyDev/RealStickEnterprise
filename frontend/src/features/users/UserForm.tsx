import { useState, type FormEvent } from 'react';

import { Button, Field, SelectField } from '../../components/ui';
import type { UserRole } from '../../types/auth';
import type { Franchise } from '../../types/franchise';
import type { ManagedUser } from '../../types/user';

export type UserFormValues = {
  full_name: string;
  email: string;
  phone: string;
  role: UserRole;
  franchise_id: string;
};

export function emptyUserForm(role: UserRole = 'SYSTEM_ADMIN'): UserFormValues {
  return {
    full_name: '',
    email: '',
    phone: '',
    role,
    franchise_id: '',
  };
}

export function userToForm(user: ManagedUser): UserFormValues {
  return {
    full_name: user.full_name,
    email: user.email ?? '',
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
  onCancel,
  onSubmit,
}: {
  mode: 'create' | 'edit';
  initial: UserFormValues;
  franchises?: Franchise[];
  franchiseLabel?: string;
  submitting: boolean;
  onCancel: () => void;
  onSubmit: (values: UserFormValues) => void;
}) {
  const [values, setValues] = useState(initial);
  const isSystemAdmin = values.role === 'SYSTEM_ADMIN';
  const showFranchiseSelect = !franchiseLabel && !isSystemAdmin;
  const showReadOnlyFranchise = Boolean(franchiseLabel);

  function update<K extends keyof UserFormValues>(key: K, value: UserFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit(values);
  }

  return (
    <form onSubmit={handleSubmit}>
      <Field
        label="Name"
        required
        value={values.full_name}
        onChange={(event) => update('full_name', event.target.value)}
      />
      <Field
        label="Email"
        type="email"
        required
        value={values.email}
        disabled={mode === 'edit'}
        onChange={(event) => update('email', event.target.value)}
      />
      <Field
        label="Phone"
        value={values.phone}
        onChange={(event) => update('phone', event.target.value)}
      />

      {mode === 'create' && !franchiseLabel ? (
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

      {isSystemAdmin ? (
        <p className="mb-4 text-xs text-[#8A8A84]">System admins are not assigned to a franchise.</p>
      ) : null}

      {mode === 'create' ? (
        <p className="mb-4 text-xs text-[#8A8A84]">
          A secure password setup invite is emailed. Passwords are never stored in profiles or shown
          here.
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
            !values.full_name.trim() ||
            (mode === 'create' && !values.email.trim()) ||
            (showFranchiseSelect && !values.franchise_id)
          }
        >
          {submitting ? 'Saving…' : mode === 'create' ? 'Create' : 'Save'}
        </Button>
      </div>
    </form>
  );
}
