import type { UserRole } from '../../types/auth';

export const OWNER_CREATE_FALLBACK = 'Unable to create owner. Please try again.';
export const OWNER_EMAIL_EXISTS = 'Email already exists. Please use a different email address.';

export const OWNER_FIELD_ERROR = {
  nameRequired: 'Name is required.',
  ownerNameRequired: 'Owner name is required.',
  emailRequired: 'Email is required.',
  ownerEmailRequired: 'Owner email is required.',
  emailInvalid: 'Invalid email format.',
  franchiseRequired: 'Franchise owner must belong to a franchise.',
} as const;

/** Matches backend AdminUserCreate / FranchiseOwnerCreate email validation. */
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export type OwnerCreateFieldErrors = Partial<{
  full_name: string;
  email: string;
  franchise_id: string;
}>;

export type OwnerCreateErrorState = {
  formError: string | null;
  fieldErrors: OwnerCreateFieldErrors;
};

export type OwnerCreateResult = {
  dialogOpen: boolean;
  error: string | null;
};

type ClassifyOptions = {
  ownerLabels?: boolean;
  requireFranchise?: boolean;
  fallback?: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object') return value as Record<string, unknown>;
  return null;
}

function httpResponse(error: unknown): { status?: number; statusText?: string; data?: unknown } | null {
  const record = asRecord(error);
  const response = record?.response;
  if (!response || typeof response !== 'object') return null;
  return response as { status?: number; statusText?: string; data?: unknown };
}

function errorMessage(error: unknown): string {
  if (typeof error === 'string') return error;
  if (error instanceof Error && error.message) return error.message;
  const record = asRecord(error);
  return typeof record?.message === 'string' ? record.message : '';
}

function cleanValidationMsg(message: string): string {
  return message.replace(/^value error,\s*/i, '').trim();
}

function detailItems(data: unknown): unknown[] {
  const record = asRecord(data);
  const detail = record?.detail ?? data;
  if (Array.isArray(detail)) return detail;
  if (typeof detail === 'string') return [detail];
  return [];
}

function locField(loc: unknown): string | null {
  if (!Array.isArray(loc) || loc.length === 0) return null;
  const last = loc[loc.length - 1];
  return typeof last === 'string' ? last : null;
}

export function ownerEmailError(value: string, ownerLabels = false): string | null {
  const trimmed = value.trim();
  if (!trimmed) return ownerLabels ? OWNER_FIELD_ERROR.ownerEmailRequired : OWNER_FIELD_ERROR.emailRequired;
  if (!EMAIL_RE.test(trimmed.toLowerCase())) return OWNER_FIELD_ERROR.emailInvalid;
  return null;
}

export function ownerNameError(value: string, ownerLabels = false): string | null {
  if (!value.trim()) return ownerLabels ? OWNER_FIELD_ERROR.ownerNameRequired : OWNER_FIELD_ERROR.nameRequired;
  return null;
}

export function ownerFranchiseError(role: UserRole, franchiseId: string): string | null {
  if (role === 'FRANCHISE_OWNER' && !franchiseId.trim()) {
    return OWNER_FIELD_ERROR.franchiseRequired;
  }
  return null;
}

export function validateOwnerForm(
  values: {
    full_name: string;
    email: string;
    role: UserRole;
    franchise_id: string;
  },
  options: ClassifyOptions = {},
): OwnerCreateFieldErrors {
  const ownerLabels = Boolean(options.ownerLabels);
  const errors: OwnerCreateFieldErrors = {};
  const name = ownerNameError(values.full_name, ownerLabels);
  const email = ownerEmailError(values.email, ownerLabels);
  const franchise =
    options.requireFranchise === false ? null : ownerFranchiseError(values.role, values.franchise_id);
  if (name) errors.full_name = name;
  if (email) errors.email = email;
  if (franchise) errors.franchise_id = franchise;
  return errors;
}

export function applyOwnerCreateResult(
  succeeded: boolean,
  errorMessage?: string | null,
): OwnerCreateResult {
  if (succeeded) {
    return { dialogOpen: false, error: null };
  }
  return {
    dialogOpen: true,
    error: errorMessage === undefined ? OWNER_CREATE_FALLBACK : errorMessage,
  };
}

function isUnsafeOwnerMessage(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) return true;
  const lower = trimmed.toLowerCase();
  if (lower.includes('axios')) return true;
  if (lower.includes('status code')) return true;
  if (/\b\d{3}\s+(bad request|unauthorized|forbidden|not found|internal server error|conflict)\b/i.test(trimmed)) {
    return true;
  }
  if (/\b(sql|postgres|psycopg|traceback|supabase|stack trace|relation|constraint|duplicate key)\b/i.test(trimmed)) {
    return true;
  }
  if (/\bdoes not exist\b/i.test(trimmed)) return true;
  if (/https?:\/\//i.test(trimmed) || /\/api\//i.test(trimmed)) return true;
  if (/\.(py|ts|tsx|js|sql)\b/i.test(trimmed)) return true;
  if (/request failed/i.test(trimmed)) return true;
  if (/\bat\s+\S+\.(py|ts|js)/i.test(trimmed)) return true;
  if (trimmed.length > 240) return true;
  return false;
}

function fieldFromMessage(message: string): keyof OwnerCreateFieldErrors | null {
  const lower = message.toLowerCase();
  if (lower.includes('email')) return 'email';
  if (/\bname is required\b|\bowner name\b|\bname cannot\b/.test(lower)) return 'full_name';
  if (/\bmust belong to a franchise\b|\bselect franchise\b/.test(lower)) return 'franchise_id';
  return null;
}

function rewriteOwnerEmailConflict(message: string): string {
  const lower = message.toLowerCase();
  if (!lower.includes('email') || !lower.includes('already exists')) return message;
  if (lower.includes('assign') || lower.includes('auth user with this email')) {
    return OWNER_EMAIL_EXISTS;
  }
  return message;
}

function safeMessage(raw: string, fallback = OWNER_CREATE_FALLBACK): string {
  const cleaned = cleanValidationMsg(raw);
  if (!cleaned || isUnsafeOwnerMessage(cleaned)) return fallback;
  const rewritten = rewriteOwnerEmailConflict(cleaned);
  return rewritten.endsWith('.') ? rewritten : `${rewritten}.`;
}

export function classifyOwnerCreateError(
  error: unknown,
  options: ClassifyOptions = {},
): OwnerCreateErrorState {
  const fallback = options.fallback ?? OWNER_CREATE_FALLBACK;
  const fieldErrors: OwnerCreateFieldErrors = {};
  const response = httpResponse(error);
  const items = detailItems(response?.data);
  const formMessages: string[] = [];

  for (const item of items) {
    if (typeof item === 'string') {
      const message = safeMessage(item, '');
      if (!message) continue;
      const field = fieldFromMessage(message);
      if (field) {
        fieldErrors[field] = message;
      } else {
        formMessages.push(message);
      }
      continue;
    }
    const row = asRecord(item);
    if (!row) continue;
    const rawMsg = typeof row.msg === 'string' ? row.msg : '';
    const message = safeMessage(rawMsg, '');
    if (!message) continue;
    const field = locField(row.loc);
    if (field === 'full_name' || field === 'email' || field === 'franchise_id') {
      fieldErrors[field] = message;
    } else {
      const inferred = fieldFromMessage(message);
      if (inferred) fieldErrors[inferred] = message;
      else formMessages.push(message);
    }
  }

  if (!items.length) {
    const raw = errorMessage(error);
    const message = raw && !isUnsafeOwnerMessage(raw) ? safeMessage(raw) : fallback;
    if (message !== fallback) {
      const field = fieldFromMessage(message);
      if (field) fieldErrors[field] = message;
      else formMessages.push(message);
    }
  }

  if (options.ownerLabels && fieldErrors.full_name && /name is required/i.test(fieldErrors.full_name)) {
    fieldErrors.full_name = OWNER_FIELD_ERROR.ownerNameRequired;
  }
  if (options.ownerLabels && fieldErrors.email && /email is required/i.test(fieldErrors.email)) {
    fieldErrors.email = OWNER_FIELD_ERROR.ownerEmailRequired;
  }

  const formError =
    Object.keys(fieldErrors).length > 0 && formMessages.length === 0
      ? null
      : formMessages[0] || (Object.keys(fieldErrors).length > 0 ? null : fallback);

  return { formError, fieldErrors };
}
