/** Safe, user-facing login messages. Never return raw HTTP/API text from these. */
export const LOGIN_ERROR = {
  invalidCredentials: 'Invalid email or password.',
  inactiveAccount: 'Your account is inactive. Please contact the administrator.',
  unauthorized: 'You are not authorized to access this application.',
  network: 'Unable to connect to the server. Please try again.',
  unknown: 'Unable to sign in. Please try again.',
} as const;

export type LoginErrorMessage = (typeof LOGIN_ERROR)[keyof typeof LOGIN_ERROR];

const KNOWN_MESSAGES = new Set<string>(Object.values(LOGIN_ERROR));

type HttpResponseShape = {
  status?: number;
  statusText?: string;
  data?: unknown;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object') return value as Record<string, unknown>;
  return null;
}

function httpResponse(error: unknown): HttpResponseShape | null {
  const record = asRecord(error);
  const response = record?.response;
  if (!response || typeof response !== 'object') return null;
  return response as HttpResponseShape;
}

function errorCode(error: unknown): string {
  const record = asRecord(error);
  return typeof record?.code === 'string' ? record.code : '';
}

function errorMessage(error: unknown): string {
  if (typeof error === 'string') return error;
  if (error instanceof Error && error.message) return error.message;
  const record = asRecord(error);
  return typeof record?.message === 'string' ? record.message : '';
}

function detailText(data: unknown): string {
  const record = asRecord(data);
  const detail = record?.detail ?? (typeof data === 'string' ? data : '');
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const row = asRecord(item);
        if (row && typeof row.msg === 'string') return row.msg;
        return typeof item === 'string' ? item : '';
      })
      .join(' ');
  }
  return '';
}

function isInactiveText(text: string): boolean {
  return /\baccount is inactive\b|\binactive account\b|\bis inactive\b|\bnot active\b/.test(text);
}

function isNetworkFailure(error: unknown, status: number | undefined, text: string, code: string): boolean {
  if (status === 502 || status === 503 || status === 504) return true;
  if (
    code === 'ERR_NETWORK' ||
    code === 'ECONNABORTED' ||
    code === 'ECONNREFUSED' ||
    code === 'ENOTFOUND' ||
    code === 'ETIMEDOUT'
  ) {
    return true;
  }
  if (/\bnetwork error\b|\bfailed to fetch\b|\bload failed\b|\btimeout\b/.test(text)) return true;
  const record = asRecord(error);
  return Boolean(record && record.request != null && record.response == null);
}

function isCredentialText(text: string): boolean {
  return (
    /\binvalid credentials\b/.test(text) ||
    /\binvalid email or password\b/.test(text) ||
    /\binvalid password\b/.test(text) ||
    /\bstatus code 401\b/.test(text) ||
    /\b401\b/.test(text) ||
    /\bunauthorized\b/.test(text)
  );
}

/**
 * Map a technical authentication failure to a safe Login-page message.
 * Classification uses HTTP status and backend `detail` when present.
 */
export function toLoginErrorMessage(error: unknown): LoginErrorMessage {
  const message = errorMessage(error);
  if (KNOWN_MESSAGES.has(message)) return message as LoginErrorMessage;

  const response = httpResponse(error);
  const status = typeof response?.status === 'number' ? response.status : undefined;
  const detail = detailText(response?.data);
  const statusText = typeof response?.statusText === 'string' ? response.statusText : '';
  const code = errorCode(error);
  const text = [message, statusText, detail, code].filter(Boolean).join(' ').toLowerCase();

  if (isInactiveText(text)) return LOGIN_ERROR.inactiveAccount;
  if (isNetworkFailure(error, status, text, code)) return LOGIN_ERROR.network;
  if (status === 403) return LOGIN_ERROR.unauthorized;
  if (status === 401 || isCredentialText(text)) return LOGIN_ERROR.invalidCredentials;
  return LOGIN_ERROR.unknown;
}
