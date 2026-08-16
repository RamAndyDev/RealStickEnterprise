import { useQuery, useMutation } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';

import { PublicPageMeta } from '../../components/layout/PublicLayout';
import { Button, ErrorBanner, Field, SelectField, SuccessBanner } from '../../components/ui';
import {
  fetchContactOptions,
  submitContactEnquiry,
  type EnquiryType,
} from '../../lib/publicApi';
import { apiErrorMessage } from '../franchises/status';

const FAILURE = 'Unable to send your enquiry right now. Please try again.';

const ENQUIRY_TYPES: { id: EnquiryType; label: string }[] = [
  { id: 'GENERAL', label: 'General Enquiry' },
  { id: 'FRANCHISE', label: 'Franchise Enquiry' },
  { id: 'COMPLAINT', label: 'Complaint' },
  { id: 'FEEDBACK', label: 'Feedback' },
  { id: 'OTHER', label: 'Other' },
];

export function ContactPage() {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [enquiryType, setEnquiryType] = useState<EnquiryType>('GENERAL');
  const [website, setWebsite] = useState('');
  const [done, setDone] = useState(false);

  const optionsQuery = useQuery({
    queryKey: ['public-contact-options'],
    queryFn: fetchContactOptions,
  });
  const options = optionsQuery.data;

  const mutation = useMutation({
    mutationFn: submitContactEnquiry,
    onSuccess: () => {
      setDone(true);
      setName('');
      setPhone('');
      setEmail('');
      setMessage('');
      setEnquiryType('GENERAL');
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
      enquiry_type: enquiryType,
      website: website.trim() || undefined,
    });
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:py-16">
      <PublicPageMeta title="Contact | RealStick" />
      <p className="text-xs font-semibold uppercase tracking-[.18em] text-[#1A7A4A]">Say hello</p>
      <h1 className="mt-2 font-serif text-4xl font-bold text-[#0D4F2E]">Contact us</h1>
      <p className="mt-3 max-w-2xl text-[#4A4A46]">
        Send a message to the RealStick team. Choose an enquiry type so we can route it correctly.
      </p>

      <section className="mt-8 rounded-3xl bg-[#0D4F2E] p-6 text-white shadow-[0_8px_30px_rgba(13,79,46,0.12)] sm:p-8">
        <h2 className="font-serif text-2xl font-bold">Contact RealStick</h2>
        <p className="mt-2 text-sm text-white/70">Reach the team directly when a number or email is configured.</p>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <DirectAction
            label="WhatsApp"
            href={options?.whatsapp_url}
            ready={Boolean(options?.whatsapp_url)}
          />
          <DirectAction
            label="Call Us"
            href={options?.tel_url}
            ready={Boolean(options?.tel_url)}
          />
          <DirectAction
            label="Email Us"
            href={options?.mailto_url}
            ready={Boolean(options?.mailto_url)}
          />
        </div>
      </section>

      <form
        onSubmit={onSubmit}
        className="relative mx-auto mt-8 max-w-[560px] rounded-3xl bg-white p-6 shadow-[0_8px_30px_rgba(13,79,46,0.06)] sm:p-8"
      >
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

        <SelectField
          label="Enquiry Type"
          name="enquiry_type"
          required
          value={enquiryType}
          onChange={(e) => setEnquiryType(e.target.value as EnquiryType)}
        >
          {ENQUIRY_TYPES.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </SelectField>
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

function DirectAction({
  label,
  href,
  ready,
}: {
  label: string;
  href: string | null | undefined;
  ready: boolean;
}) {
  if (ready && href) {
    return (
      <a
        href={href}
        target={href.startsWith('http') ? '_blank' : undefined}
        rel={href.startsWith('http') ? 'noreferrer' : undefined}
        className="flex min-h-14 items-center justify-center rounded-2xl bg-white px-4 text-sm font-semibold text-[#0D4F2E] transition hover:bg-[#E6F4EC] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
      >
        {label}
      </a>
    );
  }
  return (
    <div className="flex min-h-14 flex-col items-center justify-center rounded-2xl border border-white/20 bg-white/5 px-4 text-center">
      <span className="text-sm font-semibold text-white/70">{label}</span>
      <span className="mt-1 text-[11px] text-white/45">Configurable — not set</span>
    </div>
  );
}
