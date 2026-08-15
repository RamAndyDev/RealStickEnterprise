import { useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';

import { PublicPageMeta } from '../../components/layout/PublicLayout';
import { Button, ErrorBanner, Field, SuccessBanner } from '../../components/ui';
import { submitContactEnquiry } from '../../lib/publicApi';
import { apiErrorMessage } from '../franchises/status';

const FAILURE = 'Unable to send your enquiry right now. Please try again.';

export function ContactPage() {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [website, setWebsite] = useState('');
  const [done, setDone] = useState(false);

  const mutation = useMutation({
    mutationFn: submitContactEnquiry,
    onSuccess: () => {
      setDone(true);
      setName('');
      setPhone('');
      setEmail('');
      setMessage('');
      setWebsite('');
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setDone(false);
    mutation.mutate({
      name: name.trim(),
      phone: phone.trim(),
      email: email.trim(),
      message: message.trim(),
      website: website.trim() || undefined,
    });
  }

  return (
    <div className="mx-auto max-w-[560px] px-4 py-12 sm:px-6 lg:py-16">
      <PublicPageMeta title="Contact | RealStick" />
      <p className="text-xs font-semibold uppercase tracking-[.18em] text-[#1A7A4A]">Say hello</p>
      <h1 className="mt-2 font-serif text-4xl font-bold text-[#0D4F2E]">Contact us</h1>
      <p className="mt-3 text-[#4A4A46]">
        Send a message to the RealStick team. This is a general enquiry — not a franchise application.
      </p>

      <form onSubmit={onSubmit} className="relative mt-8 rounded-3xl bg-white p-6 shadow-[0_8px_30px_rgba(13,79,46,0.06)] sm:p-8">
        {done ? (
          <div className="mb-4">
            <SuccessBanner message="Thank you. The RealStick team will contact you." />
          </div>
        ) : null}
        {mutation.isError ? (
          <div className="mb-4">
            <ErrorBanner message={apiErrorMessage(mutation.error, FAILURE)} />
          </div>
        ) : null}

        <Field label="Name" name="name" required value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
        <Field
          label="Phone"
          name="phone"
          required
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          maxLength={20}
        />
        <Field
          label="Email"
          name="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <label className="mb-3 block">
          <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
            Message / Enquiry
          </span>
          <textarea
            name="message"
            required
            maxLength={2000}
            rows={6}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="w-full rounded-lg border border-[#E0DDD5] bg-white px-3 py-2.5 text-base outline-none focus:border-[#1A7A4A] sm:text-sm"
          />
        </label>
        <div className="absolute -left-[9999px] h-0 w-0 overflow-hidden" aria-hidden>
          <label>
            Website
            <input
              tabIndex={-1}
              autoComplete="off"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
            />
          </label>
        </div>
        <Button type="submit" className="mt-2 min-h-11 w-full" disabled={mutation.isPending}>
          {mutation.isPending ? 'Sending…' : 'Send enquiry'}
        </Button>
      </form>
    </div>
  );
}
