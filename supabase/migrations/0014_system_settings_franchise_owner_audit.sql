-- Admin-controlled Franchise Owner Audit visibility.
-- Do not modify 0001–0013. Apply this migration manually.

-- ---------------------------------------------------------------------------
-- system_settings
-- Key/value application settings managed by SYSTEM_ADMIN via FastAPI
-- (service role). Franchise Owner Audit is disabled until an Admin enables it.
-- ---------------------------------------------------------------------------

create table public.system_settings (
  key text primary key,
  value jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint system_settings_key_not_blank check (btrim(key) <> '')
);

insert into public.system_settings (key, value)
values ('franchise_owner_audit_enabled', 'false'::jsonb);

drop trigger if exists system_settings_set_updated_at on public.system_settings;
create trigger system_settings_set_updated_at
before update on public.system_settings
for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- RLS: service-role FastAPI only. No anon/authenticated policies.
-- ---------------------------------------------------------------------------

alter table public.system_settings enable row level security;
