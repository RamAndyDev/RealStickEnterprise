-- M11 Franchise Operational Audit.
-- Do not modify 0001–0009. Do not reuse quality_audits / quality_audit_items.

-- ---------------------------------------------------------------------------
-- Enum (shared by overall_status and item status)
-- ---------------------------------------------------------------------------

create type public.franchise_audit_status as enum (
  'PASS',
  'NEEDS_ATTENTION',
  'FAIL'
);

-- ---------------------------------------------------------------------------
-- franchise_audits — immutable historical snapshot (no PATCH/DELETE in API)
-- ---------------------------------------------------------------------------

create table public.franchise_audits (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid not null references public.franchises (id) on delete restrict,
  franchise_name_snapshot text not null,
  audit_date date not null,
  auditor_id uuid references public.profiles (id) on delete set null,
  auditor_name_snapshot text not null,
  overall_status public.franchise_audit_status not null,
  remarks text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.franchise_audit_items (
  id uuid primary key default gen_random_uuid(),
  audit_id uuid not null references public.franchise_audits (id) on delete cascade,
  item_key text not null,
  checklist_item text not null,
  display_order integer not null,
  status public.franchise_audit_status not null,
  remarks text,
  created_at timestamptz not null default now(),
  unique (audit_id, item_key)
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

create index idx_franchise_audits_franchise_date
  on public.franchise_audits (franchise_id, audit_date desc);

create index idx_franchise_audits_audit_date
  on public.franchise_audits (audit_date desc);

create index idx_franchise_audits_overall_status
  on public.franchise_audits (overall_status);

create index idx_franchise_audit_items_audit
  on public.franchise_audit_items (audit_id);

-- ---------------------------------------------------------------------------
-- updated_at trigger (existing project convention)
-- ---------------------------------------------------------------------------

drop trigger if exists franchise_audits_set_updated_at on public.franchise_audits;
create trigger franchise_audits_set_updated_at
before update on public.franchise_audits
for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- RLS: service-role FastAPI only. No anon/authenticated policies.
-- ---------------------------------------------------------------------------

alter table public.franchise_audits enable row level security;
alter table public.franchise_audit_items enable row level security;
