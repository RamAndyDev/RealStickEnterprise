import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from './AuthProvider';

/**
 * Foundation page for completing a Supabase password recovery.
 * Redirect URL should be configured in the Supabase Auth dashboard.
 */
export function ResetPasswordPage() {
  const { updatePassword, session } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    if (!session) {
      setError('Recovery session missing. Open the link from your email again.');
      return;
    }

    setSubmitting(true);
    try {
      await updatePassword(password);
      setDone(true);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update password.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0D4F2E] p-5">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center text-white">
          <div className="font-serif text-5xl font-bold">RealStick™</div>
          <div className="mt-2 text-xs uppercase tracking-[.2em] text-white/45">
            Choose a new password
          </div>
        </div>

        <form onSubmit={onSubmit} className="rounded-2xl bg-white p-7 shadow-2xl">
          <h1 className="mb-6 text-xl font-bold">Set new password</h1>

          {error ? (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          ) : null}
          {done ? (
            <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              Password updated.
            </div>
          ) : null}

          <label className="mb-4 block text-xs font-semibold uppercase tracking-wide text-[#8A8A84]">
            New password
            <input
              required
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 w-full rounded-lg border border-[#E0DDD5] px-3 py-3 outline-none focus:border-[#1A7A4A]"
            />
          </label>

          <label className="mb-6 block text-xs font-semibold uppercase tracking-wide text-[#8A8A84]">
            Confirm password
            <input
              required
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              className="mt-2 w-full rounded-lg border border-[#E0DDD5] px-3 py-3 outline-none focus:border-[#1A7A4A]"
            />
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-[#1A7A4A] py-3 font-semibold text-white disabled:opacity-60"
          >
            {submitting ? 'Saving…' : 'Update password'}
          </button>

          <div className="mt-5 text-center text-sm">
            <Link to="/login" className="text-[#1A7A4A] hover:underline">
              Back to sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
