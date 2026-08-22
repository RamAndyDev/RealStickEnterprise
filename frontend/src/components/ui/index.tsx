import { MoreHorizontal } from 'lucide-react';
import {
  useEffect,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from 'react';

import {
  ACTION_FIT_CLASS,
  ACTION_GROUP_ALIGN,
  ACTION_GROUP_CLASS,
  ACTION_SELECT_CLASS,
  ACTIONS_TD_CLASS,
  ACTIONS_TH_CLASS,
  type ActionFit,
} from './actionFit';

export { initialsFromName } from './initials';
export {
  ActionMenuItem,
  ActionMenuSeparator,
  AdminListCard,
  FilterSelect,
  InitialsAvatar,
  ListToolbar,
  PageHeader,
  SegmentedTabs,
  TableSkeleton,
} from './adminList';

export type { ActionFit } from './actionFit';
export {
  ACTION_FIT_CLASS,
  ACTION_GROUP_CLASS,
  ACTION_SELECT_CLASS,
  ACTIONS_TD_CLASS,
  ACTIONS_TH_CLASS,
} from './actionFit';

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'outline' | 'danger' | 'muted' | 'onDark';
  size?: 'sm' | 'md';
  fit?: ActionFit;
};

export function Button({
  children,
  className = '',
  variant = 'primary',
  size = 'md',
  fit,
  type = 'button',
  ...props
}: BtnProps) {
  const base =
    'inline-flex items-center justify-center rounded-lg font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A]';
  const sizes = fit
    ? ACTION_FIT_CLASS[fit]
    : size === 'sm'
      ? 'px-3.5 py-1.5 text-[13px]'
      : 'px-5 py-2.5 text-sm';
  const variants = {
    primary: 'bg-[#1A7A4A] text-white hover:bg-[#16693f]',
    outline: 'border-2 border-[#1A7A4A] bg-transparent text-[#1A7A4A] hover:bg-[#E6F4EC]',
    danger: 'bg-[#C00000] text-white hover:bg-[#a00000]',
    muted: 'border-2 border-[#8A8A84] bg-transparent text-[#8A8A84] hover:bg-[#f3f2ef]',
    onDark:
      'bg-white text-[#0D4F2E] hover:bg-[#E6F4EC] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white',
  }[variant];

  return (
    <button type={type} className={`${base} ${sizes} ${variants} ${className}`} {...props}>
      {children}
    </button>
  );
}

type ActionButtonBase = Omit<BtnProps, 'size' | 'fit'> & {
  fit?: Exclude<ActionFit, 'icon'>;
};

type IconActionButton = Omit<BtnProps, 'size' | 'fit'> & {
  fit: 'icon';
  'aria-label': string;
};

export type ActionButtonProps = ActionButtonBase | IconActionButton;

export function ActionButton({ fit = 'sm', className = '', title, ...props }: ActionButtonProps) {
  const accessible = 'aria-label' in props ? props['aria-label'] : undefined;
  return (
    <Button size="sm" fit={fit} className={className} title={title ?? accessible} {...props} />
  );
}

export function ActionGroup({
  children,
  align = 'start',
  className = '',
}: {
  children: ReactNode;
  align?: 'start' | 'end';
  className?: string;
}) {
  return (
    <div className={`${ACTION_GROUP_CLASS} ${ACTION_GROUP_ALIGN[align]} ${className}`.trim()}>
      {children}
    </div>
  );
}

export function ActionsTh({
  children = 'Actions',
  align = 'start',
  className = '',
}: {
  children?: ReactNode;
  align?: 'start' | 'end';
  className?: string;
}) {
  return (
    <th className={`${ACTIONS_TH_CLASS} ${align === 'end' ? 'text-right' : 'text-left'} ${className}`.trim()}>
      {children}
    </th>
  );
}

export function ActionsTd({
  children,
  align = 'start',
  className = '',
}: {
  children: ReactNode;
  align?: 'start' | 'end';
  className?: string;
}) {
  return (
    <td className={`${ACTIONS_TD_CLASS} ${align === 'end' ? 'text-right' : 'text-left'} ${className}`.trim()}>
      <ActionGroup align={align}>{children}</ActionGroup>
    </td>
  );
}

export function ActionSelect({ className = '', ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`${ACTION_SELECT_CLASS} ${className}`} {...props} />;
}

export function ActionMenu({
  label = 'More',
  children,
  icon = true,
}: {
  label?: string;
  children: ReactNode;
  icon?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={rootRef}>
      {icon ? (
        <ActionButton
          variant="muted"
          fit="icon"
          className="border-[#E0DDD5] text-[#5C5C56] hover:bg-[#F7F5F0] hover:text-[#1A1A18]"
          aria-expanded={open}
          aria-haspopup="menu"
          aria-label={label}
          title={label}
          onClick={() => setOpen((current) => !current)}
        >
          <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
        </ActionButton>
      ) : (
        <ActionButton
          variant="muted"
          aria-expanded={open}
          aria-haspopup="menu"
          aria-label={label}
          title={label}
          onClick={() => setOpen((current) => !current)}
        >
          {label}
        </ActionButton>
      )}
      {open ? (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-1 min-w-[11rem] rounded-lg border border-[#E0DDD5] bg-white p-1 shadow-[0_8px_24px_rgba(0,0,0,.12)]"
        >
          <div className="flex flex-col gap-0.5" onClick={() => setOpen(false)}>
            {children}
          </div>
        </div>
      ) : null}
    </div>
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
  variant = 'solid',
}: {
  children: ReactNode;
  tone?: 'green' | 'orange' | 'navy' | 'muted' | 'red' | 'amber';
  variant?: 'solid' | 'soft';
}) {
  const solid = {
    green: 'bg-[#1A7A4A] text-white',
    orange: 'bg-[#E8621A] text-white',
    navy: 'bg-[#1B3A6B] text-white',
    muted: 'bg-[#8A8A84] text-white',
    red: 'bg-[#C00000] text-white',
    amber: 'bg-[#D97706] text-white',
  }[tone];
  const soft = {
    green: 'bg-[#E6F4EC] text-[#0D4F2E]',
    orange: 'bg-[#FFF1E9] text-[#B44510]',
    navy: 'bg-[#E8EEF6] text-[#1B3A6B]',
    muted: 'bg-[#F3F2EF] text-[#5C5C56]',
    red: 'bg-[#FDECEC] text-[#A00000]',
    amber: 'bg-[#FEF3C7] text-[#92400E]',
  }[tone];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] tracking-[.04em] ${
        variant === 'soft' ? `font-semibold ${soft}` : `font-bold ${solid}`
      }`}
    >
      {children}
    </span>
  );
}

export function Modal({
  title,
  subtitle,
  toolbar,
  footer,
  children,
  onClose,
  wide = false,
  size,
}: {
  title: string;
  subtitle?: ReactNode;
  toolbar?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
  size?: 'md' | 'lg';
}) {
  const structured = Boolean(toolbar || footer);
  const widthClass =
    size === 'lg' ? 'max-w-[720px]' : wide ? 'max-w-[660px]' : 'max-w-[420px]';

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-label={title}
        className={`flex max-h-[90vh] w-full flex-col rounded-2xl bg-white shadow-[0_8px_40px_rgba(0,0,0,.25)] ${
          structured ? 'overflow-hidden' : 'overflow-auto'
        } ${widthClass}`}
      >
        <div className="sticky top-0 z-10 shrink-0 border-b border-[#E0DDD5] bg-white px-5 py-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 id="modal-title" className="text-[15px] font-bold text-[#1A1A18]">
                {title}
              </h2>
              {subtitle ? <div className="mt-1 text-xs text-[#8A8A84]">{subtitle}</div> : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="text-[22px] leading-none text-[#8A8A84] hover:text-[#1A1A18] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A]"
              aria-label="Close"
            >
              ×
            </button>
          </div>
        </div>
        {toolbar ? <div className="shrink-0 border-b border-[#E0DDD5] bg-white px-5 py-3">{toolbar}</div> : null}
        <div className={`px-5 py-4 ${structured ? 'min-h-0 flex-1 overflow-y-auto' : ''}`}>{children}</div>
        {footer ? (
          <div className="shrink-0 border-t border-[#E0DDD5] bg-white px-5 py-3">{footer}</div>
        ) : null}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-dashed border-[#E0DDD5] bg-white px-8 py-16 text-center">
      <p className="text-[15px] font-medium text-[#1A1A18]">{title}</p>
      {hint ? <p className="mx-auto mt-1.5 max-w-sm text-sm leading-5 text-[#8A8A84]">{hint}</p> : null}
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
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
  compact = false,
  icon,
}: {
  label: string;
  value: ReactNode;
  sub?: string;
  color?: 'green' | 'orange' | 'navy' | 'mint';
  compact?: boolean;
  icon?: ReactNode;
}) {
  const accent = {
    green: 'border-t-[#1A7A4A]',
    orange: 'border-t-[#E8621A]',
    navy: 'border-t-[#1B3A6B]',
    mint: 'border-t-[#2E9E62]',
  }[color];
  const iconTone = {
    green: 'bg-[#E6F4EC] text-[#1A7A4A]',
    orange: 'bg-[#FFF1E9] text-[#E8621A]',
    navy: 'bg-[#E8EEF6] text-[#1B3A6B]',
    mint: 'bg-[#E6F4EC] text-[#2E9E62]',
  }[color];

  if (compact) {
    return (
      <div className="flex h-full min-h-[4.75rem] items-start gap-3 rounded-xl border border-[#E8E6E0] bg-white px-4 py-3.5 shadow-[0_1px_2px_rgba(0,0,0,.04)]">
        {icon ? (
          <span
            className={`mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${iconTone}`}
            aria-hidden="true"
          >
            {icon}
          </span>
        ) : null}
        <div className="min-w-0">
          <div className="text-[11px] font-medium uppercase tracking-[.06em] text-[#8A8A84]">{label}</div>
          <div className="mt-1 font-serif text-[22px] font-bold leading-none tracking-tight text-[#1A1A18]">
            {value}
          </div>
          {sub ? <div className="mt-1 text-[11px] text-[#8A8A84]">{sub}</div> : null}
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border border-[#E0DDD5] border-t-[3px] bg-white px-[18px] py-4 ${accent}`}>
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">{label}</div>
      <div className="font-serif text-2xl font-bold tracking-tight text-[#1A1A18]">{value}</div>
      {sub ? <div className="mt-1 text-[11px] text-[#8A8A84]">{sub}</div> : null}
    </div>
  );
}
