import { Search } from 'lucide-react';
import type { ButtonHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react';

import { initialsFromName } from './initials';

export { initialsFromName } from './initials';

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="font-serif text-[26px] font-bold leading-tight text-[#1A1A18]">{title}</h1>
        {description ? (
          <p className="mt-1.5 max-w-2xl text-sm leading-5 text-[#8A8A84]">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0 sm:pt-0.5">{action}</div> : null}
    </div>
  );
}

export function ListToolbar({
  search,
  searchPlaceholder,
  onSearchChange,
  filters,
}: {
  search: string;
  searchPlaceholder: string;
  onSearchChange: (value: string) => void;
  filters?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center">
      <div className="relative lg:flex-1">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8A8A84]"
          aria-hidden="true"
        />
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={searchPlaceholder}
          aria-label="Search"
          className="w-full rounded-lg border border-[#E0DDD5] bg-white py-2.5 pl-9 pr-3 text-sm outline-none focus:border-[#1A7A4A] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A]"
        />
      </div>
      {filters ? <div className="flex flex-wrap items-center gap-2 lg:shrink-0">{filters}</div> : null}
    </div>
  );
}

export function FilterSelect({ className = '', ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`w-full rounded-lg border border-[#E0DDD5] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1A7A4A] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A] lg:w-52 ${className}`}
      {...props}
    />
  );
}

export function SegmentedTabs<T extends string>({
  items,
  value,
  onChange,
}: {
  items: { id: T; label: string }[];
  value: T;
  onChange: (id: T) => void;
}) {
  return (
    <div
      className="mb-4 inline-flex max-w-full flex-wrap gap-0.5 rounded-lg border border-[#E0DDD5] bg-[#FDFAF4] p-0.5"
      role="tablist"
    >
      {items.map((tab) => {
        const active = value === tab.id;
        return (
          <button
            key={tab.id || 'all'}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(tab.id)}
            className={`rounded-md px-3 py-1.5 text-[13px] font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A] ${
              active ? 'bg-white text-[#1A1A18] shadow-[0_1px_2px_rgba(0,0,0,.06)]' : 'text-[#5C5C56] hover:text-[#1A1A18]'
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div
      className="overflow-hidden rounded-xl border border-[#E8E6E0] bg-white shadow-[0_1px_2px_rgba(0,0,0,.04)]"
      aria-hidden="true"
    >
      <div className="border-b border-[#E8E6E0] px-5 py-3">
        <div className="h-3 w-36 rounded bg-[#EFEDE8]" />
      </div>
      {Array.from({ length: rows }, (_, index) => (
        <div
          key={index}
          className="flex items-center gap-4 border-b border-[#F0EEE8] px-5 py-4 last:border-b-0"
        >
          <div className="h-4 w-1/4 rounded bg-[#F7F5F0]" />
          <div className="h-4 w-1/5 rounded bg-[#F7F5F0]" />
          <div className="h-4 w-1/6 rounded bg-[#F7F5F0]" />
          <div className="ml-auto h-4 w-24 rounded bg-[#F7F5F0]" />
        </div>
      ))}
    </div>
  );
}

export function InitialsAvatar({ name }: { name: string }) {
  return (
    <span
      className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#E6F4EC] text-[11px] font-semibold text-[#0D4F2E]"
      aria-hidden="true"
    >
      {initialsFromName(name)}
    </span>
  );
}

export function ActionMenuItem({
  children,
  destructive = false,
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { destructive?: boolean }) {
  return (
    <button
      type="button"
      role="menuitem"
      className={`w-full rounded-md px-3 py-2 text-left text-[13px] font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A] ${
        destructive
          ? 'text-[#C00000] hover:bg-[#FDECEC]'
          : 'text-[#1A1A18] hover:bg-[#F7F5F0]'
      } ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function ActionMenuSeparator() {
  return <div className="my-1 border-t border-[#EFEDE8]" role="separator" />;
}

export function AdminListCard({ children }: { children: ReactNode }) {
  return (
    <article className="rounded-xl border border-[#E8E6E0] bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,.04)]">
      {children}
    </article>
  );
}
