import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react';

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'outline' | 'danger' | 'muted';
  size?: 'sm' | 'md';
};

export function Button({
  children,
  className = '',
  variant = 'primary',
  size = 'md',
  type = 'button',
  ...props
}: BtnProps) {
  const base =
    'inline-flex items-center justify-center rounded-lg font-semibold transition disabled:cursor-not-allowed disabled:opacity-60';
  const sizes = size === 'sm' ? 'px-3.5 py-1.5 text-[13px]' : 'px-5 py-2.5 text-sm';
  const variants = {
    primary: 'bg-[#1A7A4A] text-white hover:bg-[#16693f]',
    outline: 'border-2 border-[#1A7A4A] bg-transparent text-[#1A7A4A] hover:bg-[#E6F4EC]',
    danger: 'bg-[#C00000] text-white hover:bg-[#a00000]',
    muted: 'border-2 border-[#8A8A84] bg-transparent text-[#8A8A84] hover:bg-[#f3f2ef]',
  }[variant];

  return (
    <button type={type} className={`${base} ${sizes} ${variants} ${className}`} {...props}>
      {children}
    </button>
  );
}

type FieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
};

export function Field({ label, error, className = '', id, ...props }: FieldProps) {
  const fieldId = id ?? props.name;
  return (
    <label className="mb-3 block">
      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
        {label}
      </span>
      <input
        id={fieldId}
        className={`w-full rounded-lg border bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1A7A4A] ${
          error ? 'border-red-500' : 'border-[#E0DDD5]'
        } ${className}`}
        {...props}
      />
      {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
    </label>
  );
}

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  error?: string;
  children: ReactNode;
};

export function SelectField({ label, error, children, className = '', id, ...props }: SelectFieldProps) {
  const fieldId = id ?? props.name;
  return (
    <label className="mb-3 block">
      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
        {label}
      </span>
      <select
        id={fieldId}
        className={`w-full rounded-lg border bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1A7A4A] ${
          error ? 'border-red-500' : 'border-[#E0DDD5]'
        } ${className}`}
        {...props}
      >
        {children}
      </select>
      {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
    </label>
  );
}

export function Badge({
  children,
  tone = 'green',
}: {
  children: ReactNode;
  tone?: 'green' | 'orange' | 'navy' | 'muted' | 'red' | 'amber';
}) {
  const colors = {
    green: 'bg-[#1A7A4A]',
    orange: 'bg-[#E8621A]',
    navy: 'bg-[#1B3A6B]',
    muted: 'bg-[#8A8A84]',
    red: 'bg-[#C00000]',
    amber: 'bg-[#D97706]',
  }[tone];
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-bold tracking-[.05em] text-white ${colors}`}
    >
      {children}
    </span>
  );
}

export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`max-h-[90vh] w-full overflow-auto rounded-2xl bg-white shadow-[0_8px_40px_rgba(0,0,0,.25)] ${
          wide ? 'max-w-[660px]' : 'max-w-[420px]'
        }`}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-[#E0DDD5] bg-white px-5 py-4">
          <h2 className="text-[15px] font-bold text-[#1A1A18]">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-[22px] leading-none text-[#8A8A84] hover:text-[#1A1A18]"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-dashed border-[#E0DDD5] bg-white px-6 py-12 text-center">
      <p className="font-medium text-[#1A1A18]">{title}</p>
      {hint ? <p className="mt-1 text-sm text-[#8A8A84]">{hint}</p> : null}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {message}
    </div>
  );
}

export function SuccessBanner({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
      {message}
    </div>
  );
}

export function LoadingBlock({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="rounded-xl border border-[#E0DDD5] bg-white px-6 py-12 text-center text-sm text-[#8A8A84]">
      {label}
    </div>
  );
}

export function StatCard({
  label,
  value,
  sub,
  color = 'green',
}: {
  label: string;
  value: ReactNode;
  sub?: string;
  color?: 'green' | 'orange' | 'navy' | 'mint';
}) {
  const accent = {
    green: 'border-t-[#1A7A4A]',
    orange: 'border-t-[#E8621A]',
    navy: 'border-t-[#1B3A6B]',
    mint: 'border-t-[#2E9E62]',
  }[color];

  return (
    <div className={`rounded-xl border border-[#E0DDD5] border-t-[3px] bg-white px-[18px] py-4 ${accent}`}>
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">{label}</div>
      <div className="font-serif text-2xl font-bold tracking-tight text-[#1A1A18]">{value}</div>
      {sub ? <div className="mt-1 text-[11px] text-[#8A8A84]">{sub}</div> : null}
    </div>
  );
}
