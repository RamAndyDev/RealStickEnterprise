import { useState, type FormEvent } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { Link, Navigate } from 'react-router-dom';

import { RealStickLogo } from '../../components/branding/RealStickLogo';
import { documentTitleForRole } from '../../components/seo/documentTitle';
import { useDocumentMeta } from '../../components/seo/useDocumentMeta';
import { useAuth } from './AuthProvider';
import { toLoginErrorMessage } from './loginError';
import { staffLandingPath } from './nav';

export function LoginPage() {
  const { signIn, session, profile, loading } = useAuth();
  useDocumentMeta(
    documentTitleForRole(profile?.role) ?? 'Staff Login | RealStick',
    'Staff and POS login for RealStick Enterprise.',
  );
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  if (!loading && session && profile) {
    return <Navigate to={staffLandingPath(profile.role)} replace />;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await signIn(identifier.trim(), password);
    } catch (error) {
      setFormError(toLoginErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0D4F2E] p-5">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center text-white">
          <div className="rounded-2xl bg-white px-6 py-4 shadow-lg">
            <RealStickLogo className="h-24 w-auto sm:h-28" />
          </div>
          <div className="mt-4 text-xs uppercase tracking-[.2em] text-white/45">
            Billing & Management System
          </div>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl bg-white p-7 shadow-2xl"
        >
          <h1 className="mb-6 text-xl font-bold">Staff Login</h1>

          {formError ? (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {formError}
            </div>
          ) : null}

          <label className="mb-4 block text-xs font-semibold uppercase tracking-wide text-[#8A8A84]">
            Email/User ID
            <input
              required
              type="text"
              autoComplete="username"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              className="mt-2 w-full rounded-lg border border-[#E0DDD5] px-3 py-3 outline-none focus:border-[#1A7A4A]"
              placeholder="Enter email or user ID"
            />
          </label>

          <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-[#8A8A84]">
            Password
            <span className="relative mt-2 block">
              <input
                required
                type={passwordVisible ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-lg border border-[#E0DDD5] py-3 pl-3 pr-14 outline-none focus:border-[#1A7A4A]"
                placeholder="Enter password"
              />
              <button
                type="button"
                onClick={() => setPasswordVisible((visible) => !visible)}
                aria-label={passwordVisible ? 'Hide password' : 'Show password'}
                aria-pressed={passwordVisible}
                className="absolute inset-y-0 right-0 flex min-h-11 min-w-11 items-center justify-center rounded-r-lg text-[#6F706A] hover:text-[#1A7A4A] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#1A7A4A]"
              >
                {passwordVisible ? (
                  <EyeOff size={20} aria-hidden="true" />
                ) : (
                  <Eye size={20} aria-hidden="true" />
                )}
              </button>
            </span>
          </label>

          <div className="mb-6 text-right">
            <Link
              to="/forgot-password"
              className="text-sm text-[#1A7A4A] hover:underline"
            >
              Forgot password?
            </Link>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-[#1A7A4A] py-3 font-semibold text-white disabled:opacity-60"
          >
            {submitting ? 'Signing in…' : 'Sign In →'}
          </button>
        </form>
      </div>
    </div>
  );
}
