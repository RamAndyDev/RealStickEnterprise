export const EMPLOYEE_SESSION_STORAGE_KEY = 'realstick.employeeSessionId';

export function storeEmployeeSessionId(id: string | null | undefined): void {
  if (typeof sessionStorage === 'undefined') return;
  if (id) {
    sessionStorage.setItem(EMPLOYEE_SESSION_STORAGE_KEY, id);
    return;
  }
  sessionStorage.removeItem(EMPLOYEE_SESSION_STORAGE_KEY);
}

export function readEmployeeSessionId(): string | null {
  if (typeof sessionStorage === 'undefined') return null;
  return sessionStorage.getItem(EMPLOYEE_SESSION_STORAGE_KEY);
}

export function clearEmployeeSessionId(): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.removeItem(EMPLOYEE_SESSION_STORAGE_KEY);
}
