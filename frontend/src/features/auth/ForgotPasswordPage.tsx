import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from './AuthProvider';

/** Password-reset request foundation (Supabase email recovery). */
export function ForgotPasswordPage() {
  const { requestPasswordReset } = useAuth();
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      await requestPasswordReset(email.trim());
      setMessage(
        'If an account exists for that email, a reset link has been sent. Check your inbox.',
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to send reset email.');
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
            Password reset for email accounts
          </div>
        </div>

        <form onSubmit={onSubmit} className="rounded-2xl bg-white p-7 shadow-2xl">
          <h1 className="mb-2 text-xl font-bold">Reset your password</h1>
          <p className="mb-6 text-sm text-[#8A8A84]">
            Enter your admin or owner email. Employees do not have email recovery — ask the
            franchise owner to reset the password.
          </p>

          {error ? (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          ) : null}
          {message ? (
            <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              {message}
            </div>
          ) : null}

          <label className="mb-6 block text-xs font-semibold uppercase tracking-wide text-[#8A8A84]">
            Email
            <input
              required
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-2 w-full rounded-lg border border-[#E0DDD5] px-3 py-3 outline-none focus:border-[#1A7A4A]"
              placeholder="you@realstick.in"
            />
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-[#1A7A4A] py-3 font-semibold text-white disabled:opacity-60"
          >
            {submitting ? 'Sending…' : 'Send reset link'}
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
