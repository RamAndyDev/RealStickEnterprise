-- RealStick Enterprise — production MVP schema
-- Run on a clean Supabase project (auth.users must exist).

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------

create type public.user_role as enum (
  'SYSTEM_ADMIN',
  'FRANCHISE_OWNER',
  'EMPLOYEE'
);

create type public.franchise_status as enum (
  'APPLICATION',
  'PENDING_PAYMENT',
  'SETUP',
  'ACTIVE',
  'SUSPENDED',
  'CLOSED'
);

create type public.franchise_application_status as enum (
  'SUBMITTED',
  'UNDER_REVIEW',
  'APPROVED',
  'REJECTED',
  'CONVERTED'
);

create type public.order_status as enum (
  'DRAFT',
  'COMPLETED',
  'CANCELLED'
);

create type public.payment_method as enum (
  'CASH',
  'UPI',
  'CARD',
  'QR'
);

create type public.inventory_movement_type as enum (
  'OPENING',
  'PURCHASE',
  'CONSUMPTION',
  'ADJUSTMENT',
  'WASTAGE',
  'RETURN'
);

create type public.quality_audit_status as enum (
  'DRAFT',
  'SUBMITTED',
  'ARCHIVED'
);

create type public.gallery_media_type as enum (
  'IMAGE',
  'VIDEO'
);

-- ---------------------------------------------------------------------------
-- Shared trigger helpers
-- ---------------------------------------------------------------------------

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create or replace function public.enforce_profile_role_franchise_rules()
returns trigger
language plpgsql
as $$
declare
  employee_count integer;
  max_employees integer;
begin
  if new.role = 'SYSTEM_ADMIN' then
    if new.franchise_id is not null then
      raise exception 'SYSTEM_ADMIN profiles must not belong to a franchise';
    end if;
  elsif new.role in ('FRANCHISE_OWNER', 'EMPLOYEE') then
    if new.franchise_id is null then
      raise exception '% profiles must belong to a franchise', new.role;
    end if;
  end if;

  if new.role = 'EMPLOYEE' and new.is_active then
    select f.employee_limit
    into max_employees
    from public.franchises f
    where f.id = new.franchise_id;

    if max_employees is null then
      raise exception 'Franchise not found for employee profile';
    end if;

    select count(*)
    into employee_count
    from public.profiles
    where franchise_id = new.franchise_id
      and role = 'EMPLOYEE'
      and is_active = true
      and id is distinct from new.id;

    if employee_count >= max_employees then
      raise exception 'Maximum of % active employees allowed per franchise', max_employees;
    end if;
  end if;

  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- Franchise domain
-- (franchises first — no circular FK with profiles; owner link lives on profiles)
-- ---------------------------------------------------------------------------

create table public.franchises (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  code text unique,
  owner_email text,
  address text,
  city text,
  state text,
  postal_code text,
  tier text,
  status public.franchise_status not null default 'APPLICATION',
  open_date date,
  closed_at timestamptz,
  employee_limit integer not null default 10
    check (employee_limit > 0 and employee_limit <= 10),
  settings jsonb not null default '{}'::jsonb,
  is_archived boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.franchise_applications (
  id uuid primary key default gen_random_uuid(),
  applicant_name text not null,
  email text not null,
  phone text,
  city text,
  state text,
  investment_range text,
  message text,
  status public.franchise_application_status not null default 'SUBMITTED',
  reviewed_by uuid,
  reviewed_at timestamptz,
  converted_franchise_id uuid references public.franchises (id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.franchise_payments (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid not null references public.franchises (id),
  amount numeric(12, 2) not null check (amount >= 0),
  currency text not null default 'INR',
  payment_method text,
  reference_number text,
  status text not null default 'PENDING'
    check (status in ('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED')),
  paid_at timestamptz,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.launch_checklist_items (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid not null references public.franchises (id),
  item_key text not null,
  item_name text not null,
  display_order integer not null default 0,
  is_completed boolean not null default false,
  completed_at timestamptz,
  completed_by uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (franchise_id, item_key)
);

-- ---------------------------------------------------------------------------
-- Identity (profiles references auth.users; franchise link avoids reverse FK)
-- ---------------------------------------------------------------------------

create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text not null,
  role public.user_role not null,
  franchise_id uuid references public.franchises (id),
  phone text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint profiles_role_franchise_check check (
    (role = 'SYSTEM_ADMIN' and franchise_id is null)
    or (role in ('FRANCHISE_OWNER', 'EMPLOYEE') and franchise_id is not null)
  )
);

alter table public.franchise_applications
  add constraint franchise_applications_reviewed_by_fkey
  foreign key (reviewed_by) references public.profiles (id);

alter table public.launch_checklist_items
  add constraint launch_checklist_items_completed_by_fkey
  foreign key (completed_by) references public.profiles (id);

create unique index idx_profiles_one_active_owner_per_franchise
  on public.profiles (franchise_id)
  where role = 'FRANCHISE_OWNER' and is_active = true;

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

create trigger profiles_enforce_role_and_employee_limit
  before insert or update on public.profiles
  for each row execute function public.enforce_profile_role_franchise_rules();

-- ---------------------------------------------------------------------------
-- Product catalog
-- ---------------------------------------------------------------------------

-- Flat menu: product_categories is the MVP category structure
-- (prototype five categories). No nested menu hierarchy.
create table public.product_categories (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  display_order integer not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.products (
  id uuid primary key default gen_random_uuid(),
  category_id uuid references public.product_categories (id),
  sku text unique,
  name text not null,
  description text,
  image_url text,
  price numeric(12, 2) not null check (price >= 0),
  min_price numeric(12, 2),
  max_price numeric(12, 2),
  is_active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint products_price_bounds_check check (
    (min_price is null or min_price >= 0)
    and (max_price is null or max_price >= 0)
    and (min_price is null or max_price is null or min_price <= max_price)
  )
);

-- Franchise assignment + selling price. products.price is the catalog/base price.
-- SYSTEM_ADMIN assigns products; FRANCHISE_OWNER may change selling_price.
create table public.franchise_product_prices (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid not null references public.franchises (id),
  product_id uuid not null references public.products (id),
  selling_price numeric(12, 2) not null check (selling_price >= 0),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (franchise_id, product_id)
);

-- Single centrally managed GST rate. Orders snapshot gst_rate at sale time.
create table public.gst_settings (
  id uuid primary key default gen_random_uuid(),
  rate numeric(5, 2) not null check (rate between 0 and 100),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index idx_gst_settings_one_active
  on public.gst_settings ((true))
  where is_active = true;

-- ---------------------------------------------------------------------------
-- Inventory & recipes
-- Ledger in inventory_movements; current balance in franchise_ingredient_stock.
-- Atomic deduction is implemented later in the FastAPI order service.
-- ---------------------------------------------------------------------------

create table public.ingredients (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  unit text not null,
  reorder_level numeric(14, 3) not null default 0 check (reorder_level >= 0),
  cost_per_unit numeric(12, 4) not null default 0 check (cost_per_unit >= 0),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.recipes (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null unique references public.products (id),
  name text,
  yield_quantity numeric(12, 3) not null default 1 check (yield_quantity > 0),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.recipe_items (
  id uuid primary key default gen_random_uuid(),
  recipe_id uuid not null references public.recipes (id),
  ingredient_id uuid not null references public.ingredients (id),
  quantity numeric(14, 4) not null check (quantity > 0),
  unit text not null,
  created_at timestamptz not null default now(),
  unique (recipe_id, ingredient_id)
);

create table public.inventory_movements (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid not null references public.franchises (id),
  ingredient_id uuid not null references public.ingredients (id),
  movement_type public.inventory_movement_type not null,
  quantity numeric(14, 4) not null check (quantity > 0),
  reference_type text,
  reference_id uuid,
  notes text,
  created_by uuid references public.profiles (id),
  created_at timestamptz not null default now(),
  constraint inventory_movements_reference_pair_check check (
    (reference_type is null and reference_id is null)
    or (reference_type is not null and reference_id is not null)
  )
);

create table public.franchise_ingredient_stock (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid not null references public.franchises (id),
  ingredient_id uuid not null references public.ingredients (id),
  current_quantity numeric(14, 4) not null default 0,
  updated_at timestamptz not null default now(),
  unique (franchise_id, ingredient_id)
);

-- ---------------------------------------------------------------------------
-- POS
-- ---------------------------------------------------------------------------

create table public.discounts (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  percentage numeric(5, 2) not null check (percentage between 0 and 100),
  franchise_id uuid references public.franchises (id),
  valid_from timestamptz,
  valid_until timestamptz,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint discounts_validity_window_check check (
    valid_from is null or valid_until is null or valid_from <= valid_until
  )
);

create table public.coupons (
  id uuid primary key default gen_random_uuid(),
  code text not null,
  description text,
  percentage numeric(5, 2) check (percentage between 0 and 100),
  fixed_amount numeric(12, 2) check (fixed_amount >= 0),
  max_uses integer check (max_uses is null or max_uses > 0),
  used_count integer not null default 0 check (used_count >= 0),
  valid_from timestamptz,
  valid_until timestamptz,
  franchise_id uuid references public.franchises (id),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint coupons_value_type_check check (
    (percentage is not null and fixed_amount is null)
    or (percentage is null and fixed_amount is not null)
  ),
  constraint coupons_validity_window_check check (
    valid_from is null or valid_until is null or valid_from <= valid_until
  )
);

create unique index idx_coupons_code_global
  on public.coupons (lower(code))
  where franchise_id is null;

create unique index idx_coupons_code_per_franchise
  on public.coupons (franchise_id, lower(code))
  where franchise_id is not null;

create table public.orders (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid not null references public.franchises (id),
  bill_number text not null,
  status public.order_status not null default 'DRAFT',
  customer_phone text,
  subtotal numeric(12, 2) not null default 0 check (subtotal >= 0),
  discount_amount numeric(12, 2) not null default 0 check (discount_amount >= 0),
  discount_id uuid references public.discounts (id),
  coupon_id uuid references public.coupons (id),
  taxable_amount numeric(12, 2) not null default 0 check (taxable_amount >= 0),
  gst_rate numeric(5, 2) not null default 0 check (gst_rate between 0 and 100),
  gst_amount numeric(12, 2) not null default 0 check (gst_amount >= 0),
  total_amount numeric(12, 2) not null default 0 check (total_amount >= 0),
  payment_method public.payment_method,
  cashier_id uuid references public.profiles (id),
  completed_at timestamptz,
  cancelled_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (franchise_id, bill_number),
  constraint orders_completed_requires_payment_check check (
    (
      status = 'COMPLETED'
      and payment_method is not null
      and completed_at is not null
    )
    or (status = 'CANCELLED' and cancelled_at is not null)
    or (status = 'DRAFT')
  )
);

create table public.order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.orders (id),
  product_id uuid not null references public.products (id),
  product_name_snapshot text not null,
  unit_price numeric(12, 2) not null check (unit_price >= 0),
  quantity integer not null check (quantity > 0),
  line_discount_amount numeric(12, 2) not null default 0 check (line_discount_amount >= 0),
  line_total numeric(12, 2) not null check (line_total >= 0),
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Public website & operations
-- ---------------------------------------------------------------------------

create table public.gallery_items (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid references public.franchises (id),
  title text,
  caption text,
  media_type public.gallery_media_type not null,
  storage_path text not null,
  media_url text not null,
  display_order integer not null default 0,
  is_approved boolean not null default false,
  is_archived boolean not null default false,
  uploaded_by uuid references public.profiles (id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.quality_audits (
  id uuid primary key default gen_random_uuid(),
  franchise_id uuid not null references public.franchises (id),
  auditor_id uuid references public.profiles (id),
  status public.quality_audit_status not null default 'DRAFT',
  overall_score numeric(5, 2) not null default 0 check (overall_score between 0 and 100),
  notes text,
  submitted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.quality_audit_items (
  id uuid primary key default gen_random_uuid(),
  audit_id uuid not null references public.quality_audits (id),
  criterion text not null,
  score numeric(5, 2) not null check (score between 0 and 100),
  notes text,
  created_at timestamptz not null default now(),
  unique (audit_id, criterion)
);

-- ---------------------------------------------------------------------------
-- updated_at triggers (tables not covered above)
-- ---------------------------------------------------------------------------

create trigger franchises_set_updated_at
  before update on public.franchises
  for each row execute function public.set_updated_at();

create trigger franchise_applications_set_updated_at
  before update on public.franchise_applications
  for each row execute function public.set_updated_at();

create trigger franchise_payments_set_updated_at
  before update on public.franchise_payments
  for each row execute function public.set_updated_at();

create trigger launch_checklist_items_set_updated_at
  before update on public.launch_checklist_items
  for each row execute function public.set_updated_at();

create trigger product_categories_set_updated_at
  before update on public.product_categories
  for each row execute function public.set_updated_at();

create trigger products_set_updated_at
  before update on public.products
  for each row execute function public.set_updated_at();

create trigger franchise_product_prices_set_updated_at
  before update on public.franchise_product_prices
  for each row execute function public.set_updated_at();

create trigger gst_settings_set_updated_at
  before update on public.gst_settings
  for each row execute function public.set_updated_at();

create trigger ingredients_set_updated_at
  before update on public.ingredients
  for each row execute function public.set_updated_at();

create trigger franchise_ingredient_stock_set_updated_at
  before update on public.franchise_ingredient_stock
  for each row execute function public.set_updated_at();

create trigger recipes_set_updated_at
  before update on public.recipes
  for each row execute function public.set_updated_at();

create trigger discounts_set_updated_at
  before update on public.discounts
  for each row execute function public.set_updated_at();

create trigger coupons_set_updated_at
  before update on public.coupons
  for each row execute function public.set_updated_at();

create trigger orders_set_updated_at
  before update on public.orders
  for each row execute function public.set_updated_at();

create trigger gallery_items_set_updated_at
  before update on public.gallery_items
  for each row execute function public.set_updated_at();

create trigger quality_audits_set_updated_at
  before update on public.quality_audits
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

create index idx_franchises_status on public.franchises (status) where not is_archived;
create index idx_franchise_applications_status on public.franchise_applications (status, created_at desc);
create index idx_franchise_applications_email on public.franchise_applications (lower(email));
create index idx_franchise_applications_converted
  on public.franchise_applications (converted_franchise_id)
  where converted_franchise_id is not null;
create index idx_franchise_payments_franchise on public.franchise_payments (franchise_id, created_at desc);
create index idx_launch_checklist_franchise on public.launch_checklist_items (franchise_id, display_order);

create index idx_profiles_franchise on public.profiles (franchise_id) where franchise_id is not null;
create index idx_profiles_role on public.profiles (role) where is_active = true;

create index idx_products_category on public.products (category_id) where is_active = true;
create index idx_products_active on public.products (is_active, name);
create index idx_franchise_product_prices_franchise
  on public.franchise_product_prices (franchise_id)
  where is_active = true;
create index idx_franchise_product_prices_product
  on public.franchise_product_prices (product_id);

create index idx_recipe_items_recipe on public.recipe_items (recipe_id);
create index idx_recipe_items_ingredient on public.recipe_items (ingredient_id);

create index idx_inventory_movements_franchise_ingredient
  on public.inventory_movements (franchise_id, ingredient_id, created_at desc);
create index idx_inventory_movements_reference
  on public.inventory_movements (reference_type, reference_id)
  where reference_id is not null;
create index idx_franchise_ingredient_stock_low
  on public.franchise_ingredient_stock (franchise_id, current_quantity);

create index idx_discounts_franchise on public.discounts (franchise_id) where is_active = true;
create index idx_coupons_franchise on public.coupons (franchise_id) where is_active = true;

create index idx_orders_franchise_created on public.orders (franchise_id, created_at desc);
create index idx_orders_franchise_status on public.orders (franchise_id, status);
create index idx_orders_cashier on public.orders (cashier_id) where cashier_id is not null;
create index idx_order_items_order on public.order_items (order_id);
create index idx_order_items_product on public.order_items (product_id);

create index idx_gallery_franchise on public.gallery_items (franchise_id, display_order)
  where not is_archived;
create index idx_gallery_approved on public.gallery_items (is_approved, media_type, created_at desc)
  where not is_archived;

create index idx_quality_audits_franchise on public.quality_audits (franchise_id, created_at desc);
create index idx_quality_audit_items_audit on public.quality_audit_items (audit_id);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- Backend uses the service-role key (bypasses RLS). Client access is restricted.
-- ---------------------------------------------------------------------------

alter table public.franchises enable row level security;
alter table public.franchise_applications enable row level security;
alter table public.franchise_payments enable row level security;
alter table public.launch_checklist_items enable row level security;
alter table public.profiles enable row level security;
alter table public.product_categories enable row level security;
alter table public.products enable row level security;
alter table public.ingredients enable row level security;
alter table public.recipes enable row level security;
alter table public.recipe_items enable row level security;
alter table public.inventory_movements enable row level security;
alter table public.discounts enable row level security;
alter table public.coupons enable row level security;
alter table public.orders enable row level security;
alter table public.order_items enable row level security;
alter table public.gallery_items enable row level security;
alter table public.quality_audits enable row level security;
alter table public.quality_audit_items enable row level security;

-- Authenticated users may read their own profile only.
create policy profiles_select_own
  on public.profiles
  for select
  to authenticated
  using (id = auth.uid());

-- Authenticated franchise members may read their franchise row.
create policy franchises_select_member
  on public.franchises
  for select
  to authenticated
  using (
    exists (
      select 1
      from public.profiles p
      where p.id = auth.uid()
        and p.is_active = true
        and p.franchise_id = franchises.id
    )
  );

-- Approved, non-archived gallery items are readable by anyone (public website).
create policy gallery_items_select_public
  on public.gallery_items
  for select
  to anon, authenticated
  using (is_approved = true and not is_archived);

-- No INSERT/UPDATE/DELETE policies for anon or authenticated on application tables.
-- All writes go through FastAPI with the service-role key until auth policies are added.
