-- Observation #11: employee login/logout session tracking.
-- Do not modify 0001–0012. Franchise owners view history via FastAPI (service role).

-- ---------------------------------------------------------------------------
-- Enum
-- ---------------------------------------------------------------------------

create type public.employee_session_status as enum (
  'ACTIVE',
  'COMPLETED'
);

-- ---------------------------------------------------------------------------
-- employee_sessions
-- One row per successful employee login. Explicit logout completes the row.
-- Unexpected browser/device close may leave status ACTIVE and logout_at NULL.
-- ---------------------------------------------------------------------------

create table public.employee_sessions (
  id uuid primary key default gen_random_uuid(),
  employee_id uuid not null references public.profiles (id) on delete restrict,
  employee_name_snapshot text not null,
  auth_session_id text not null,
  login_at timestamptz not null default now(),
  logout_at timestamptz,
  status public.employee_session_status not null default 'ACTIVE',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint employee_sessions_name_snapshot_not_blank check (btrim(employee_name_snapshot) <> ''),
  constraint employee_sessions_auth_session_id_not_blank check (btrim(auth_session_id) <> ''),
  constraint employee_sessions_logout_status_check check (
    (status = 'ACTIVE' and logout_at is null)
    or (status = 'COMPLETED' and logout_at is not null)
  )
);

create index idx_employee_sessions_employee_login
  on public.employee_sessions (employee_id, login_at desc);

create index idx_employee_sessions_status
  on public.employee_sessions (status);

create unique index employee_sessions_active_auth_session_unique
  on public.employee_sessions (auth_session_id)
  where status = 'ACTIVE';

-- ---------------------------------------------------------------------------
-- Ensure employee_id always points at an EMPLOYEE profile
-- ---------------------------------------------------------------------------

create or replace function public.enforce_employee_session_employee_role()
returns trigger
language plpgsql
as $$
declare
  v_role public.user_role;
begin
  select p.role
  into v_role
  from public.profiles p
  where p.id = new.employee_id;

  if v_role is distinct from 'EMPLOYEE' then
    raise exception 'employee_sessions.employee_id must reference an EMPLOYEE profile';
  end if;

  return new;
end;
$$;

drop trigger if exists employee_sessions_enforce_employee_role on public.employee_sessions;
create trigger employee_sessions_enforce_employee_role
before insert or update of employee_id on public.employee_sessions
for each row execute function public.enforce_employee_session_employee_role();

drop trigger if exists employee_sessions_set_updated_at on public.employee_sessions;
create trigger employee_sessions_set_updated_at
before update on public.employee_sessions
for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- RLS: service-role FastAPI only. No anon/authenticated policies.
-- ---------------------------------------------------------------------------

alter table public.employee_sessions enable row level security;
