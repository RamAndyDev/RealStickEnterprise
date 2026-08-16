export const INACTIVITY_TIMEOUT_MS = 10 * 60 * 1000;
export const WARNING_BEFORE_MS = 60 * 1000;
export const INACTIVITY_WARNING_MESSAGE =
  'Your session will expire soon due to inactivity.';

export const ACTIVITY_EVENTS = [
  'mousedown',
  'keydown',
  'touchstart',
  'pointerdown',
] as const;

export function shouldWarn(idleMs: number): boolean {
  return idleMs >= INACTIVITY_TIMEOUT_MS - WARNING_BEFORE_MS && idleMs < INACTIVITY_TIMEOUT_MS;
}

export function shouldLogout(idleMs: number): boolean {
  return idleMs >= INACTIVITY_TIMEOUT_MS;
}
