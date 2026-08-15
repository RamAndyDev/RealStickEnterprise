import { useState, type FormEvent } from 'react';

import { Button, ErrorBanner, Field, SuccessBanner } from '../../components/ui';
import { changeOwnPassword } from '../../lib/usersApi';
import { apiErrorMessage } from '../franchises/status';

export function ChangePasswordPage() {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFeedback(null);

    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      const result = await changeOwnPassword(password);
      setFeedback(result.message);
      setPassword('');
      setConfirm('');
    } catch (err) {
      setError(apiErrorMessage(err, 'Unable to update password.'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">Change Password</h1>
      <p className="mt-1 text-sm text-[#8A8A84]">Update the password for your signed-in account.</p>

      <form onSubmit={onSubmit} className="mt-5 rounded-xl border border-[#E0DDD5] bg-white p-6">
        {error ? (
          <div className="mb-3">
            <ErrorBanner message={error} />
          </div>
        ) : null}
        {feedback ? (
          <div className="mb-3">
            <SuccessBanner message={feedback} />
          </div>
        ) : null}

        <Field
          label="New password"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <Field
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          required
          value={confirm}
          onChange={(event) => setConfirm(event.target.value)}
        />

        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? 'Saving…' : 'Update password'}
        </Button>
      </form>
    </div>
  );
}
