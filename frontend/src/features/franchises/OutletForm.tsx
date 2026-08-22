import { useMemo, useState, type FormEvent } from 'react';

import { Button, ErrorBanner, Field, SelectField } from '../../components/ui';
import {
  FRANCHISE_STATUSES,
  FRANCHISE_TIERS,
  type Franchise,
  type FranchiseStatus,
  type FranchiseTier,
  type FranchiseWritePayload,
} from '../../types/franchise';
import {
  validateOwnerForm,
  type OwnerCreateFieldErrors,
} from '../users/ownerForm';

export type OutletFormValues = {
  name: string;
  city: string;
  state: string;
  address: string;
  postal_code: string;
  owner_full_name: string;
  owner_email: string;
  owner_phone: string;
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
    owner_full_name: '',
    owner_email: '',
    owner_phone: '',
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
    owner_full_name: franchise.owner?.full_name ?? '',
    owner_email: franchise.owner_email ?? '',
    owner_phone: franchise.owner?.phone ?? '',
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
  {
    requireStatus = true,
    requireOwner = false,
  }: { requireStatus?: boolean; requireOwner?: boolean } = {},
): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!values.name.trim()) errors.name = 'Outlet name is required';
  if (requireOwner) {
    const ownerErrors = validateOwnerForm(
      {
        full_name: values.owner_full_name,
        email: values.owner_email,
        role: 'FRANCHISE_OWNER',
        franchise_id: '',
      },
      { ownerLabels: true, requireFranchise: false },
    );
    if (ownerErrors.full_name) errors.owner_full_name = ownerErrors.full_name;
    if (ownerErrors.email) errors.owner_email = ownerErrors.email;
  } else if (values.owner_email.trim() && !EMAIL_RE.test(values.owner_email.trim())) {
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

export function toOwnerCreatePayload(values: OutletFormValues): {
  full_name: string;
  email: string;
  phone?: string;
} {
  return {
    full_name: values.owner_full_name.trim(),
    email: values.owner_email.trim(),
    phone: values.owner_phone.trim() || undefined,
  };
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
    ...(includeStatus
      ? {
          status: values.status,
          owner_full_name: values.owner_full_name.trim() || null,
          owner_phone: values.owner_phone.trim() || null,
        }
      : {}),
  };
}

export function OutletForm({
  initial,
  mode,
  submitting,
  formError = null,
  apiFieldErrors,
  onSubmit,
  onCancel,
  onClearSubmitError,
}: {
  initial: OutletFormValues;
  mode: 'create' | 'edit';
  submitting: boolean;
  formError?: string | null;
  apiFieldErrors?: OwnerCreateFieldErrors;
  onSubmit: (values: OutletFormValues) => void;
  onCancel: () => void;
  onClearSubmitError?: () => void;
}) {
  const [values, setValues] = useState<OutletFormValues>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const isCreate = mode === 'create';

  const titleAction = useMemo(() => (isCreate ? 'Add Outlet' : 'Save Changes'), [isCreate]);
  const ownerNameError = errors.owner_full_name || apiFieldErrors?.full_name;
  const ownerEmailError = errors.owner_email || apiFieldErrors?.email;

  function update<K extends keyof OutletFormValues>(key: K, value: OutletFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
    if (errors[key]) {
      setErrors((current) => {
        if (!current[key]) return current;
        const next = { ...current };
        delete next[key];
        return next;
      });
    }
    if (formError || apiFieldErrors?.full_name || apiFieldErrors?.email) {
      onClearSubmitError?.();
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const nextErrors = validateOutletForm(values, {
      requireStatus: isCreate,
      requireOwner: isCreate,
    });
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    onSubmit(values);
  }

  return (
    <form onSubmit={handleSubmit} noValidate={isCreate}>
      {formError ? (
        <div className="mb-3">
          <ErrorBanner message={formError} />
        </div>
      ) : null}

      <div className="grid gap-0 sm:grid-cols-2 sm:gap-x-3">
        <Field
          label="Outlet Name"
          value={values.name}
          onChange={(e) => update('name', e.target.value)}
          error={errors.name}
          required
        />
        <Field
          label="City"
          value={values.city}
          onChange={(e) => update('city', e.target.value)}
        />
      </div>

      <Field
        label="Address"
        value={values.address}
        onChange={(e) => update('address', e.target.value)}
      />

      <div className="grid gap-0 sm:grid-cols-2 sm:gap-x-3">
        <Field
          label="State"
          value={values.state}
          onChange={(e) => update('state', e.target.value)}
        />
        <Field
          label="Postal Code"
          value={values.postal_code}
          onChange={(e) => update('postal_code', e.target.value)}
        />
      </div>

      {isCreate ? null : (
        <Field
          label="Owner Email"
          type="email"
          value={values.owner_email}
          onChange={(e) => update('owner_email', e.target.value)}
          error={errors.owner_email}
        />
      )}

      <div className="grid gap-0 sm:grid-cols-2 sm:gap-x-3">
        <SelectField
          label="Tier"
          value={values.tier}
          onChange={(e) => update('tier', e.target.value as FranchiseTier)}
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
          onChange={(e) => update('open_date', e.target.value)}
          error={errors.open_date}
        />
      </div>

      <div className="grid gap-0 sm:grid-cols-2 sm:gap-x-3">
        <Field
          label="Outlet Code"
          value={values.code}
          onChange={(e) => update('code', e.target.value)}
          placeholder="Optional unique code"
        />
        {isCreate ? (
          <SelectField
            label="Status"
            value={values.status}
            onChange={(e) => update('status', e.target.value as FranchiseStatus)}
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

      {isCreate ? (
        <>
          <div className="mb-3 mt-1 border-t border-[#E0DDD5] pt-3">
            <h3 className="text-sm font-semibold text-[#1A1A18]">Outlet owner</h3>
            <p className="mt-1 text-xs text-[#8A8A84]">
              This creates the outlet and its owner together. A secure password setup invite is
              emailed. Passwords are never stored in profiles or shown here.
            </p>
          </div>
          <Field
            label="Owner Name"
            value={values.owner_full_name}
            onChange={(e) => update('owner_full_name', e.target.value)}
            error={ownerNameError}
            required
          />
          <Field
            label="Owner Email"
            type="email"
            value={values.owner_email}
            onChange={(e) => update('owner_email', e.target.value)}
            error={ownerEmailError}
            required
          />
          <Field
            label="Owner Phone"
            value={values.owner_phone}
            onChange={(e) => update('owner_phone', e.target.value)}
          />
        </>
      ) : null}

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
