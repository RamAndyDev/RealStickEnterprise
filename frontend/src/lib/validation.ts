/** Shared field validators. Backend remains authoritative. */

export const FIELD_ERROR = {
  required: 'This field is required.',
  emailInvalid: 'Invalid email format.',
  phoneInvalid: 'Enter a valid Indian phone number, such as +919876543210 or 9876543210.',
  priceInvalid: 'Enter a valid price with up to 2 decimal places.',
  amountInvalid: 'Enter a valid amount with up to 2 decimal places.',
  percentageInvalid: 'Enter a valid percentage with up to 2 decimal places.',
  quantityInvalid: 'Enter a valid whole number quantity.',
} as const;

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MONEY_RE = /^\d+(\.\d{1,2})?$/;
const PHONE_RE = /^(?:\+91|91)?[6-9]\d{9}$/;
const CONTROL_RE = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/;

export function compactPhone(value: string): string {
  return value.trim().replace(/[\s-]+/g, '');
}

export function validateRequiredText(
  value: string,
  requiredMessage: string = FIELD_ERROR.required,
  maxLength = 200,
): string | null {
  const trimmed = value.trim();
  if (!trimmed) return requiredMessage;
  if (CONTROL_RE.test(trimmed)) return 'This field contains invalid characters.';
  if (trimmed.length > maxLength) return `Must be at most ${maxLength} characters.`;
  return null;
}

export function validateEmail(value: string, required = false): string | null {
  const trimmed = value.trim();
  if (!trimmed) return required ? 'Email is required.' : null;
  if (!EMAIL_RE.test(trimmed.toLowerCase())) return FIELD_ERROR.emailInvalid;
  return null;
}

export function validatePhone(value: string, required = false): string | null {
  const trimmed = value.trim();
  if (!trimmed) return required ? 'Phone is required.' : null;
  if (!PHONE_RE.test(compactPhone(trimmed))) return FIELD_ERROR.phoneInvalid;
  return null;
}

type MoneyOptions = {
  requiredMessage?: string;
  invalidMessage?: string;
  minMessage?: string;
  requirePositive?: boolean;
  allowZero?: boolean;
  max?: number;
  maxMessage?: string;
};

function validateMoney(value: string, options: MoneyOptions = {}): string | null {
  const trimmed = value.trim();
  const invalid = options.invalidMessage ?? FIELD_ERROR.amountInvalid;
  if (!trimmed) return options.requiredMessage ?? FIELD_ERROR.required;
  if (!MONEY_RE.test(trimmed)) return invalid;
  const amount = Number(trimmed);
  if (!Number.isFinite(amount)) return invalid;
  if (options.requirePositive && amount <= 0) {
    return options.minMessage ?? 'Must be greater than 0.';
  }
  if (!options.requirePositive && !options.allowZero && amount < 0) {
    return options.minMessage ?? 'Cannot be negative.';
  }
  if (options.allowZero && amount < 0) {
    return options.minMessage ?? 'Cannot be negative.';
  }
  if (options.max != null && amount > options.max) {
    return options.maxMessage ?? `Must be at most ${options.max}.`;
  }
  return null;
}

export function validatePrice(
  value: string,
  options: MoneyOptions & { allowZero?: boolean } = {},
): string | null {
  return validateMoney(value, {
    requiredMessage: options.requiredMessage ?? 'Price is required.',
    invalidMessage: options.invalidMessage ?? FIELD_ERROR.priceInvalid,
    minMessage: options.minMessage,
    requirePositive: options.requirePositive ?? !options.allowZero,
    allowZero: options.allowZero,
    max: options.max,
    maxMessage: options.maxMessage,
  });
}

export function validateAmount(value: string, options: MoneyOptions = {}): string | null {
  return validateMoney(value, {
    requiredMessage: options.requiredMessage ?? 'Amount is required.',
    invalidMessage: options.invalidMessage ?? FIELD_ERROR.amountInvalid,
    minMessage: options.minMessage ?? 'Amount must be greater than 0.',
    requirePositive: true,
    ...options,
  });
}

export function validatePercentage(
  value: string,
  options: { required?: boolean; min?: number; max?: number; allowZero?: boolean } = {},
): string | null {
  const max = options.max ?? 100;
  const allowZero = options.allowZero ?? true;
  return validateMoney(value, {
    requiredMessage: options.required === false ? undefined : 'Percentage is required.',
    invalidMessage: FIELD_ERROR.percentageInvalid,
    minMessage: allowZero ? 'Percentage cannot be negative.' : 'Percentage must be greater than 0.',
    requirePositive: !allowZero,
    allowZero,
    max,
    maxMessage: `Percentage must be at most ${max}.`,
  });
}

export function validateQuantity(
  value: string,
  { min = 1, max = 999 }: { min?: number; max?: number } = {},
): string | null {
  const trimmed = value.trim();
  if (!trimmed) return 'Quantity is required.';
  if (!/^\d+$/.test(trimmed)) return FIELD_ERROR.quantityInvalid;
  const qty = Number(trimmed);
  if (!Number.isInteger(qty) || qty < min || qty > max) {
    return `Quantity must be between ${min} and ${max}.`;
  }
  return null;
}

export function validateIsoDate(value: string, requiredMessage: string = 'Enter a valid date.'): string | null {
  const trimmed = value.trim();
  if (!trimmed) return requiredMessage;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return 'Enter a valid date.';
  const [year, month, day] = trimmed.split('-').map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== day
  ) {
    return 'Enter a valid date.';
  }
  return null;
}

export function validateDateRange(
  start: string,
  end: string,
): { start?: string; end?: string } {
  const startError = start ? validateIsoDate(start) : null;
  const endError = end ? validateIsoDate(end) : null;
  const errors: { start?: string; end?: string } = {};
  if (startError) errors.start = startError;
  if (endError) errors.end = endError;
  if (!startError && !endError && start && end && start > end) {
    errors.end = 'Start date cannot be after end date.';
  }
  return errors;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object') return value as Record<string, unknown>;
  return null;
}

export function isUnsafeApiMessage(text: string): boolean {
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

export function safeApiErrorMessage(error: unknown, fallback: string): string {
  if (
    error &&
    typeof error === 'object' &&
    'response' in error &&
    error.response &&
    typeof error.response === 'object' &&
    'data' in error.response
  ) {
    const data = (error.response as { data?: { detail?: unknown } }).data;
    const detail = data?.detail;
    if (typeof detail === 'string') {
      const cleaned = detail.replace(/^value error,\s*/i, '').trim();
      if (cleaned && !isUnsafeApiMessage(cleaned)) {
        return cleaned.endsWith('.') ? cleaned : `${cleaned}.`;
      }
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (item && typeof item === 'object' && 'msg' in item) {
            return String((item as { msg: string }).msg).replace(/^value error,\s*/i, '').trim();
          }
          return typeof item === 'string' ? item : '';
        })
        .filter((message) => message && !isUnsafeApiMessage(message));
      if (messages[0]) {
        return messages[0].endsWith('.') ? messages[0] : `${messages[0]}.`;
      }
    }
  }
  const record = asRecord(error);
  const raw = error instanceof Error ? error.message : typeof record?.message === 'string' ? record.message : '';
  if (raw && !isUnsafeApiMessage(raw)) {
    return raw.endsWith('.') ? raw : `${raw}.`;
  }
  return fallback;
}
