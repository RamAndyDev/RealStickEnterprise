import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  LOGIN_ERROR,
  toLoginErrorMessage,
} from '../src/features/auth/loginError.ts';

const root = dirname(fileURLToPath(import.meta.url));
const loginPage = readFileSync(join(root, '../src/features/auth/LoginPage.tsx'), 'utf8');
const authProvider = readFileSync(join(root, '../src/features/auth/AuthProvider.tsx'), 'utf8');

function axiosLikeError(options: {
  status?: number;
  statusText?: string;
  detail?: unknown;
  message?: string;
  code?: string;
  network?: boolean;
}) {
  const error = new Error(
    options.message ??
      (options.status != null ? `Request failed with status code ${options.status}` : 'Error'),
  );
  const response =
    options.network || options.status == null
      ? undefined
      : {
          status: options.status,
          statusText: options.statusText,
          data: options.detail !== undefined ? { detail: options.detail } : {},
        };
  Object.assign(error, {
    isAxiosError: true,
    code: options.code,
    response,
    request: options.network ? {} : response ? {} : undefined,
  });
  return error;
}

describe('toLoginErrorMessage', () => {
  it('maps invalid credentials to a generic email/password message', () => {
    assert.equal(
      toLoginErrorMessage(axiosLikeError({ status: 401, detail: 'Invalid credentials' })),
      LOGIN_ERROR.invalidCredentials,
    );
    assert.equal(toLoginErrorMessage(LOGIN_ERROR.invalidCredentials), 'Invalid email or password.');
  });

  it('maps 401 Unauthorized without leaking HTTP details', () => {
    const message = toLoginErrorMessage(
      axiosLikeError({
        status: 401,
        statusText: 'Unauthorized',
        message: 'Request failed with status code 401',
      }),
    );
    assert.equal(message, LOGIN_ERROR.invalidCredentials);
    assert.equal(message.includes('401'), false);
    assert.equal(message.toLowerCase().includes('unauthorized'), false);
    assert.equal(
      toLoginErrorMessage(new Error('401 Unauthorized')),
      LOGIN_ERROR.invalidCredentials,
    );
  });

  it('maps 403 access denied to an authorization message', () => {
    assert.equal(
      toLoginErrorMessage(
        axiosLikeError({
          status: 403,
          statusText: 'Forbidden',
          detail: 'User profile not found',
        }),
      ),
      LOGIN_ERROR.unauthorized,
    );
    assert.equal(
      toLoginErrorMessage(
        axiosLikeError({ status: 403, detail: 'Insufficient permissions for this resource' }),
      ),
      'You are not authorized to access this application.',
    );
  });

  it('maps inactive-account backend detail when it can be distinguished', () => {
    assert.equal(
      toLoginErrorMessage(
        axiosLikeError({ status: 403, detail: 'User account is inactive' }),
      ),
      LOGIN_ERROR.inactiveAccount,
    );
    assert.equal(
      toLoginErrorMessage(new Error('User account is inactive')),
      'Your account is inactive. Please contact the administrator.',
    );
  });

  it('maps network and server failures to a connection message', () => {
    assert.equal(
      toLoginErrorMessage(axiosLikeError({ network: true, code: 'ERR_NETWORK', message: 'Network Error' })),
      LOGIN_ERROR.network,
    );
    assert.equal(
      toLoginErrorMessage(axiosLikeError({ status: 503, detail: 'Unable to sign in right now' })),
      'Unable to connect to the server. Please try again.',
    );
  });

  it('maps unknown failures to a generic safe login message', () => {
    assert.equal(toLoginErrorMessage(undefined), LOGIN_ERROR.unknown);
    assert.equal(toLoginErrorMessage({ weird: true }), LOGIN_ERROR.unknown);
    assert.equal(toLoginErrorMessage(new Error('something exploded')), LOGIN_ERROR.unknown);
  });

  it('does not expose raw technical error details to the user', () => {
    const cases = [
      new Error('Request failed with status code 401'),
      axiosLikeError({ status: 500, detail: 'relation "profiles" does not exist' }),
      axiosLikeError({
        status: 500,
        detail: 'JWT signing failed at https://internal.supabase.local/auth/v1',
      }),
      new Error('AxiosError: timeout of 15000ms exceeded'),
      { response: { status: 401, data: { detail: { stack: 'Error: boom\n    at login.py:12' } } } },
    ];
    for (const error of cases) {
      const message = toLoginErrorMessage(error);
      assert.equal(Object.values(LOGIN_ERROR).includes(message), true, message);
      assert.equal(message.includes('401'), false, message);
      assert.equal(message.includes('status code'), false, message);
      assert.equal(message.includes('profiles'), false, message);
      assert.equal(message.includes('supabase'), false, message);
      assert.equal(message.includes('stack'), false, message);
      assert.equal(message.includes('login.py'), false, message);
      assert.equal(message.includes('Axios'), false, message);
    }
  });
});

describe('LoginPage password visibility', () => {
  it('starts hidden and toggles visibility without replacing the password value', () => {
    assert.match(loginPage, /const \[passwordVisible, setPasswordVisible\] = useState\(false\)/);
    assert.match(loginPage, /type=\{passwordVisible \? 'text' : 'password'\}/);
    assert.match(loginPage, /autoComplete="current-password"/);
    assert.match(loginPage, /value=\{password\}/);
    assert.match(loginPage, /setPasswordVisible\(\(visible\) => !visible\)/);
  });

  it('uses an accessible non-submit toggle with a tablet-friendly target', () => {
    assert.match(loginPage, /type="button"[\s\S]*aria-label=\{passwordVisible \? 'Hide password' : 'Show password'\}/);
    assert.match(loginPage, /aria-pressed=\{passwordVisible\}/);
    assert.match(loginPage, /min-h-11 min-w-11/);
    assert.match(loginPage, /pr-14/);
  });
});

describe('LoginPage error display and retry', () => {
  it('shows mapped errors in the existing login form error area', () => {
    assert.equal(loginPage.includes('toLoginErrorMessage'), true);
    assert.equal(loginPage.includes('formError'), true);
    assert.equal(loginPage.includes('border-red-200 bg-red-50'), true);
    assert.equal(loginPage.includes('dialog'), false);
    assert.equal(loginPage.includes('window.alert'), false);
  });

  it('stops the login loading state after failure so the user can retry', () => {
    assert.match(loginPage, /setSubmitting\(true\)/);
    assert.match(loginPage, /finally \{\s*setSubmitting\(false\);/s);
    assert.match(loginPage, /disabled=\{submitting\}/);
    const catchBlock = loginPage.slice(loginPage.indexOf('} catch (error)'), loginPage.indexOf('} finally'));
    assert.equal(catchBlock.includes("setIdentifier('')"), false);
    assert.equal(catchBlock.includes("setPassword('')"), false);
    assert.equal(catchBlock.includes('toLoginErrorMessage(error)'), true);
  });

  it('keeps successful login routing unchanged', () => {
    assert.equal(loginPage.includes('staffLandingPath(profile.role)'), true);
    assert.equal(loginPage.includes('await signIn(identifier.trim(), password)'), true);
    assert.equal(loginPage.includes('Navigate to={staffLandingPath(profile.role)} replace'), true);
  });
});

describe('AuthProvider login error mapping', () => {
  it('maps sign-in failures before they reach the login page', () => {
    assert.equal(authProvider.includes('toLoginErrorMessage'), true);
    assert.equal(authProvider.includes("await loadProfile(sessionData.session, { rethrow: true })"), true);
    assert.equal(authProvider.includes("console.error('Sign-in failed', err)"), true);
    assert.equal(authProvider.includes("api.post<{"), true);
    assert.equal(authProvider.includes("'/auth/login'"), true);
  });
});
