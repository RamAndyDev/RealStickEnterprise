import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  EMPLOYEE_ACTIVITY_LOAD_ERROR,
  formatActivityDate,
  formatActivityTime,
  logoutDisplay,
  sessionStatusLabel,
  toEmployeeActivityError,
} from '../src/features/users/employeeActivity.ts';

const root = dirname(fileURLToPath(import.meta.url));
const usersPage = readFileSync(join(root, '../src/features/users/UsersPage.tsx'), 'utf8');
const activityDialog = readFileSync(
  join(root, '../src/features/users/EmployeeActivityDialog.tsx'),
  'utf8',
);
const employeesPage = readFileSync(join(root, '../src/features/users/EmployeesPage.tsx'), 'utf8');
const usersApi = readFileSync(join(root, '../src/lib/usersApi.ts'), 'utf8');
const authProvider = readFileSync(join(root, '../src/features/auth/AuthProvider.tsx'), 'utf8');
const nav = readFileSync(join(root, '../src/features/auth/nav.ts'), 'utf8');

const activeSession = {
  status: 'ACTIVE' as const,
  logout_at: null,
  login_at: '2026-08-21T09:10:00.000Z',
};

const completedSession = {
  status: 'COMPLETED' as const,
  logout_at: '2026-08-21T12:35:00.000Z',
  login_at: '2026-08-21T09:10:00.000Z',
};

describe('employee activity display', () => {
  it('shows Currently Logged In and Logged In for an active session', () => {
    assert.equal(logoutDisplay(activeSession), 'Currently Logged In');
    assert.equal(sessionStatusLabel(activeSession), 'Logged In');
  });

  it('shows the logout time and Completed for a completed session', () => {
    const logout = logoutDisplay(completedSession);
    assert.notEqual(logout, 'Currently Logged In');
    assert.notEqual(logout, '—');
    assert.equal(logout.includes('2026-08-21T12:35:00.000Z'), false);
    assert.equal(sessionStatusLabel(completedSession), 'Completed');
    assert.match(formatActivityTime(completedSession.logout_at), /\d/);
  });

  it('formats activity dates without returning the raw ISO value', () => {
    const date = formatActivityDate(completedSession.login_at);
    assert.match(date, /Aug/i);
    assert.equal(date.includes('2026-08-21T09:10:00.000Z'), false);
  });
});

describe('employee activity error handling', () => {
  it('uses a friendly message and never shows raw backend errors', () => {
    const cases = [
      undefined,
      new Error('Request failed with status code 500'),
      { response: { status: 401, data: { detail: 'relation "employee_sessions" does not exist' } } },
      { response: { status: 500, data: { detail: 'AxiosError: timeout of 15000ms exceeded' } } },
      new Error('Traceback (most recent call last):\n  File "repository.py"'),
    ];
    for (const error of cases) {
      const message = toEmployeeActivityError(error);
      assert.equal(message, EMPLOYEE_ACTIVITY_LOAD_ERROR);
      assert.equal(message.includes('500'), false);
      assert.equal(message.includes('401'), false);
      assert.equal(message.includes('Axios'), false);
      assert.equal(message.includes('employee_sessions'), false);
      assert.equal(message.includes('Traceback'), false);
      assert.equal(message.includes('repository.py'), false);
    }
  });
});

describe('Owner Employees activity UI', () => {
  it('keeps the Employees nav item for franchise owners only', () => {
    assert.match(
      nav,
      /label: 'Employees',\s*path: '\/employees',\s*roles: \['FRANCHISE_OWNER'\]/,
    );
    assert.equal(nav.includes("path: '/employees',\n    roles: ['SYSTEM_ADMIN']"), false);
  });

  it('adds login status and View Activity on the owner Employees page', () => {
    assert.equal(employeesPage.includes('View Activity'), true);
    assert.equal(employeesPage.includes('Logged In'), true);
    assert.equal(employeesPage.includes('Logged Out'), true);
    assert.equal(employeesPage.includes('setActivityTarget(item)'), true);
    assert.equal(employeesPage.includes('EmployeeActivityDialog'), true);
    assert.equal(employeesPage.includes('/admin/employees'), false);
  });

  it('opens the Employee Activity dialog from View Activity', () => {
    assert.equal(activityDialog.includes('title="Employee Activity"'), true);
    assert.equal(activityDialog.includes('Close'), true);
    assert.equal(usersApi.includes('/owner/employees/${employeeId}/sessions'), true);
    assert.equal(usersApi.includes('/admin/employees'), false);
  });

  it('renders session history with loading, empty, and error states', () => {
    assert.equal(activityDialog.includes('Date'), true);
    assert.equal(activityDialog.includes('Login'), true);
    assert.equal(activityDialog.includes('Logout'), true);
    assert.equal(activityDialog.includes('Status'), true);
    assert.equal(activityDialog.includes('formatActivityDate'), true);
    assert.equal(activityDialog.includes('logoutDisplay'), true);
    assert.equal(activityDialog.includes('sessionStatusLabel'), true);
    assert.equal(activityDialog.includes('Loading activity…'), true);
    assert.equal(activityDialog.includes('No login activity yet'), true);
    assert.equal(activityDialog.includes('toEmployeeActivityError'), true);
    assert.equal(EMPLOYEE_ACTIVITY_LOAD_ERROR, 'Unable to load employee activity. Please try again.');
    assert.equal(activityDialog.includes('query.error.message'), false);
    assert.equal(activityDialog.includes('status code'), false);
  });
});

describe('Admin User Management has no employee tracking', () => {
  it('does not add an Employees tracking tab or activity UI', () => {
    assert.equal(usersPage.includes("{ id: 'EMPLOYEE', label: 'Employees' }"), false);
    assert.equal(usersPage.includes('View Activity'), false);
    assert.equal(usersPage.includes('Logged In'), false);
    assert.equal(usersPage.includes('Logged Out'), false);
    assert.equal(usersPage.includes('EmployeeActivityDialog'), false);
    assert.equal(usersPage.includes('listAdminEmployees'), false);
    assert.equal(usersPage.includes('/admin/employees'), false);
  });
});

describe('AuthProvider employee session tracking', () => {
  it('stores the employee session id after a successful login', () => {
    assert.equal(authProvider.includes('storeEmployeeSessionId(data.employee_session_id)'), true);
    assert.equal(authProvider.includes("'/auth/login'"), true);
    assert.equal(authProvider.includes('toLoginErrorMessage'), true);
  });

  it('records logout without blocking sign-out when tracking fails', () => {
    assert.equal(authProvider.includes("'/auth/employee-sessions/logout'"), true);
    assert.equal(authProvider.includes("console.error('Employee session tracking failed on logout'"), true);
    assert.equal(authProvider.includes('clearEmployeeSessionId()'), true);
    assert.equal(authProvider.includes('await supabase.auth.signOut()'), true);
    const signOut = authProvider.slice(authProvider.indexOf('const signOut'), authProvider.indexOf('const requestPasswordReset'));
    assert.equal(signOut.includes('try {'), true);
    assert.equal(signOut.includes('} catch (err) {'), true);
    assert.equal(signOut.includes('await supabase.auth.signOut()'), true);
    assert.ok(signOut.indexOf('} catch (err) {') < signOut.indexOf('await supabase.auth.signOut()'));
  });
});
