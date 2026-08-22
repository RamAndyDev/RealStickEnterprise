export const FRANCHISE_OWNER_AUDIT_SETTING_KEY = 'franchise_owner_audit_enabled';

export const FRANCHISE_AUDIT_SETTING_COPY = {
  heading: 'Franchise Audit',
  label: 'Allow Franchise Owners to access Audit',
  description: 'Controls whether the Audit feature is available to Franchise Owners.',
  saveSuccess: 'Franchise Audit access updated.',
  saveError: 'Unable to update Franchise Audit access. Please try again.',
  loadError: 'Unable to load Franchise Audit access.',
} as const;

export function franchiseAuditSettingStateLabel(enabled: boolean): 'On' | 'Off' {
  return enabled ? 'On' : 'Off';
}

export function resolveFranchiseAuditToggle(
  previous: boolean,
  next: boolean,
  saved: boolean,
): { value: boolean; error: string | null; feedback: string | null } {
  if (saved) {
    return {
      value: next,
      error: null,
      feedback: FRANCHISE_AUDIT_SETTING_COPY.saveSuccess,
    };
  }
  return {
    value: previous,
    error: FRANCHISE_AUDIT_SETTING_COPY.saveError,
    feedback: null,
  };
}
