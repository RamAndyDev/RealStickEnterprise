import { useMemo, useState, type FormEvent } from 'react';

import { Button, Field, SelectField } from '../../components/ui';
import {
  FRANCHISE_STATUSES,
  FRANCHISE_TIERS,
  type Franchise,
  type FranchiseStatus,
  type FranchiseTier,
  type FranchiseWritePayload,
} from '../../types/franchise';

export type OutletFormValues = {
  name: string;
  city: string;
  state: string;
  address: string;
  postal_code: string;
  owner_email: string;
  tier: FranchiseTier;
  open_date: string;
  code: string;
  status: FranchiseStatus;
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function emptyOutletForm(defaults?: Partial<OutletFormValues>): OutletFormValues {
  return {
    name: '',
    city: '',
    state: '',
    address: '',
    postal_code: '',
    owner_email: '',
    tier: 'Founder',
    open_date: '',
    code: '',
    status: 'SETUP',
    ...defaults,
  };
}

export function franchiseToForm(franchise: Franchise): OutletFormValues {
  return {
    name: franchise.name,
    city: franchise.city ?? '',
    state: franchise.state ?? '',
    address: franchise.address ?? '',
    postal_code: franchise.postal_code ?? '',
    owner_email: franchise.owner_email ?? '',
    tier: (FRANCHISE_TIERS.includes(franchise.tier as FranchiseTier)
      ? franchise.tier
      : 'Founder') as FranchiseTier,
    open_date: franchise.open_date ?? '',
    code: franchise.code ?? '',
    status: franchise.status,
  };
}

export function validateOutletForm(
  values: OutletFormValues,
  { requireStatus = true }: { requireStatus?: boolean } = {},
): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!values.name.trim()) errors.name = 'Outlet name is required';
  if (values.owner_email.trim() && !EMAIL_RE.test(values.owner_email.trim())) {
    errors.owner_email = 'Enter a valid email address';
  }
  if (!FRANCHISE_TIERS.includes(values.tier)) {
    errors.tier = 'Select a valid partner tier';
  }
  if (requireStatus && !FRANCHISE_STATUSES.includes(values.status)) {
    errors.status = 'Select a valid franchise status';
  }
  if (values.open_date) {
    const d = new Date(values.open_date);
    if (Number.isNaN(d.getTime())) errors.open_date = 'Enter a valid date';
  }
  return errors;
}

export function toWritePayload(values: OutletFormValues, includeStatus: boolean): FranchiseWritePayload {
  return {
    name: values.name.trim(),
    city: values.city.trim() || null,
    state: values.state.trim() || null,
    address: values.address.trim() || null,
    postal_code: values.postal_code.trim() || null,
    owner_email: values.owner_email.trim().toLowerCase() || null,
    tier: values.tier,
    open_date: values.open_date || null,
    code: values.code.trim() || null,
    ...(includeStatus ? { status: values.status } : {}),
  };
}

export function OutletForm({
  initial,
  mode,
  submitting,
  onSubmit,
  onCancel,
}: {
  initial: OutletFormValues;
  mode: 'create' | 'edit';
  submitting: boolean;
  onSubmit: (values: OutletFormValues) => void;
  onCancel: () => void;
}) {
  const [values, setValues] = useState<OutletFormValues>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const titleAction = useMemo(() => (mode === 'create' ? 'Add Outlet' : 'Save Changes'), [mode]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const nextErrors = validateOutletForm(values, { requireStatus: mode === 'create' });
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    onSubmit(values);
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="grid gap-0 sm:grid-cols-2 sm:gap-x-3">
        <Field
          label="Outlet Name"
          value={values.name}
          onChange={(e) => setValues((v) => ({ ...v, name: e.target.value }))}
          error={errors.name}
          required
        />
        <Field
          label="City"
          value={values.city}
          onChange={(e) => setValues((v) => ({ ...v, city: e.target.value }))}
        />
      </div>

      <Field
        label="Address"
        value={values.address}
        onChange={(e) => setValues((v) => ({ ...v, address: e.target.value }))}
      />

      <div className="grid gap-0 sm:grid-cols-2 sm:gap-x-3">
        <Field
          label="State"
          value={values.state}
          onChange={(e) => setValues((v) => ({ ...v, state: e.target.value }))}
        />
        <Field
          label="Postal Code"
          value={values.postal_code}
          onChange={(e) => setValues((v) => ({ ...v, postal_code: e.target.value }))}
        />
      </div>

      <Field
        label="Owner Email"
        type="email"
        value={values.owner_email}
        onChange={(e) => setValues((v) => ({ ...v, owner_email: e.target.value }))}
        error={errors.owner_email}
      />

      <div className="grid gap-0 sm:grid-cols-2 sm:gap-x-3">
        <SelectField
          label="Tier"
          value={values.tier}
          onChange={(e) => setValues((v) => ({ ...v, tier: e.target.value as FranchiseTier }))}
          error={errors.tier}
        >
          {FRANCHISE_TIERS.map((tier) => (
            <option key={tier} value={tier}>
              {tier} Partner
            </option>
          ))}
        </SelectField>
        <Field
          label="Open Date"
          type="date"
          value={values.open_date}
          onChange={(e) => setValues((v) => ({ ...v, open_date: e.target.value }))}
          error={errors.open_date}
        />
      </div>

      <div className="grid gap-0 sm:grid-cols-2 sm:gap-x-3">
        <Field
          label="Outlet Code"
          value={values.code}
          onChange={(e) => setValues((v) => ({ ...v, code: e.target.value }))}
          placeholder="Optional unique code"
        />
        {mode === 'create' ? (
          <SelectField
            label="Status"
            value={values.status}
            onChange={(e) => setValues((v) => ({ ...v, status: e.target.value as FranchiseStatus }))}
            error={errors.status}
          >
            {FRANCHISE_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status.replaceAll('_', ' ')}
              </option>
            ))}
          </SelectField>
        ) : (
          <div />
        )}
      </div>

      <div className="mt-2 flex justify-end gap-2">
        <Button variant="muted" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : titleAction}
        </Button>
      </div>
    </form>
  );
}
