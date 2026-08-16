-- Post-M10 business corrections: employee login_id, admin promotions,
-- optional promotion_id on discounts, and the product-images bucket.
-- Do not modify 0001–0008.

-- ---------------------------------------------------------------------------
-- Employee User ID (login_id). Admin/Owner continue to use email.
-- ---------------------------------------------------------------------------

alter table public.profiles
  add column if not exists login_id text;

update public.profiles
set login_id = null
where login_id is not null
  and btrim(login_id) = '';

create unique index if not exists profiles_login_id_unique
  on public.profiles (lower(login_id))
  where login_id is not null;

-- ---------------------------------------------------------------------------
-- Admin promotions (internal business controls — not customer coupons)
-- ---------------------------------------------------------------------------

create table if not exists public.promotions (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  promo_code text not null,
  valid_from timestamptz,
  valid_to timestamptz,
  is_active boolean not null default true,
  created_by uuid references public.profiles (id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint promotions_validity_window_check check (
    valid_from is null or valid_to is null or valid_from <= valid_to
  ),
  constraint promotions_promo_code_not_blank check (btrim(promo_code) <> '')
);

create unique index if not exists promotions_promo_code_unique
  on public.promotions (lower(promo_code));

create table if not exists public.promotion_franchises (
  id uuid primary key default gen_random_uuid(),
  promotion_id uuid not null references public.promotions (id) on delete cascade,
  franchise_id uuid not null references public.franchises (id),
  created_at timestamptz not null default now(),
  unique (promotion_id, franchise_id)
);

create index if not exists idx_promotion_franchises_franchise
  on public.promotion_franchises (franchise_id);

alter table public.promotions enable row level security;
alter table public.promotion_franchises enable row level security;

drop trigger if exists set_promotions_updated_at on public.promotions;
create trigger set_promotions_updated_at
before update on public.promotions
for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Extend existing discounts (franchise offers). promotion_id NULL = local offer.
-- ---------------------------------------------------------------------------

alter table public.discounts
  add column if not exists promotion_id uuid references public.promotions (id),
  add column if not exists created_by uuid references public.profiles (id);

create index if not exists idx_discounts_promotion
  on public.discounts (promotion_id)
  where promotion_id is not null;

-- ---------------------------------------------------------------------------
-- product-images bucket (was referenced by the app but never created)
-- ---------------------------------------------------------------------------

do $$
begin
  insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
  values (
    'product-images',
    'product-images',
    true,
    5242880,
    array['image/jpeg', 'image/png', 'image/webp']
  )
  on conflict (id) do update
    set public = excluded.public,
        file_size_limit = excluded.file_size_limit,
        allowed_mime_types = excluded.allowed_mime_types;
end
$$;

drop policy if exists "Public read product images" on storage.objects;
create policy "Public read product images"
on storage.objects
for select
to public
using (bucket_id = 'product-images');

-- ---------------------------------------------------------------------------
-- POS checkout: linked offers require an active, in-window, in-scope promotion
-- ---------------------------------------------------------------------------

create or replace function public.complete_pos_order(
  p_franchise_id uuid,
  p_cashier_id uuid,
  p_cashier_role text,
  p_payment_method public.payment_method,
  p_customer_phone text,
  p_offer_id uuid,
  p_items jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_franchise record;
  v_cashier record;
  v_offer record;
  v_promotion record;
  v_gst_rate numeric(5, 2);
  v_cgst_rate numeric(5, 2);
  v_sgst_rate numeric(5, 2);
  v_discount_value numeric(5, 2) := null;
  v_discount_type text := null;
  v_offer_name text := null;
  v_subtotal numeric(12, 2) := 0;
  v_discount_amount numeric(12, 2) := 0;
  v_taxable numeric(12, 2) := 0;
  v_cgst_amount numeric(12, 2) := 0;
  v_sgst_amount numeric(12, 2) := 0;
  v_gst_amount numeric(12, 2) := 0;
  v_total numeric(12, 2) := 0;
  v_seq integer;
  v_bill_number text;
  v_order_id uuid;
  v_now timestamptz := now();
  v_item jsonb;
  v_product_id uuid;
  v_qty numeric;
  r record;
  v_product record;
  v_category record;
  v_assignment record;
  v_unit numeric(12, 2);
  v_line_total numeric(12, 2);
  v_items_out jsonb := '[]'::jsonb;
  v_phone text;
  v_attempt integer;
begin
  if p_franchise_id is null then
    raise exception 'POS_ERROR:FRANCHISE_NOT_FOUND';
  end if;

  select *
  into v_franchise
  from public.franchises
  where id = p_franchise_id
  for update;

  if not found then
    raise exception 'POS_ERROR:FRANCHISE_NOT_FOUND';
  end if;

  select *
  into v_cashier
  from public.profiles
  where id = p_cashier_id;

  if not found or v_cashier.is_active is not true then
    raise exception 'POS_ERROR:CASHIER_INVALID';
  end if;

  if v_cashier.franchise_id is distinct from p_franchise_id then
    raise exception 'POS_ERROR:FRANCHISE_MISMATCH';
  end if;

  if p_cashier_role <> 'EMPLOYEE' or v_cashier.role <> 'EMPLOYEE' then
    raise exception 'POS_ERROR:ROLE_NOT_ALLOWED';
  end if;

  if p_payment_method not in ('CASH', 'UPI', 'CARD') then
    raise exception 'POS_ERROR:INVALID_PAYMENT';
  end if;

  v_phone := nullif(btrim(coalesce(p_customer_phone, '')), '');

  if p_items is null or jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items) = 0 then
    raise exception 'POS_ERROR:EMPTY_CART';
  end if;

  if jsonb_array_length(p_items) > 100 then
    raise exception 'POS_ERROR:CART_TOO_LARGE';
  end if;

  for v_item in select value from jsonb_array_elements(p_items)
  loop
    if v_item->>'product_id' is null then
      raise exception 'POS_ERROR:INVALID_ITEM';
    end if;
    begin
      v_product_id := (v_item->>'product_id')::uuid;
    exception
      when others then
        raise exception 'POS_ERROR:INVALID_ITEM';
    end;
    if jsonb_typeof(v_item->'quantity') <> 'number' then
      raise exception 'POS_ERROR:INVALID_QUANTITY';
    end if;
    v_qty := (v_item->>'quantity')::numeric;
    if v_qty <> trunc(v_qty) or v_qty < 1 or v_qty > 999 then
      raise exception 'POS_ERROR:INVALID_QUANTITY';
    end if;
  end loop;

  select rate
  into v_gst_rate
  from public.gst_settings
  where is_active = true
  limit 1
  for update;

  if v_gst_rate is null then
    raise exception 'POS_ERROR:GST_UNAVAILABLE';
  end if;

  v_cgst_rate := round(v_gst_rate / 2, 2);
  v_sgst_rate := round(v_gst_rate / 2, 2);
  if v_cgst_rate + v_sgst_rate <> v_gst_rate then
    raise exception 'POS_ERROR:GST_UNAVAILABLE';
  end if;

  if p_offer_id is not null then
    select *
    into v_offer
    from public.discounts
    where id = p_offer_id
    for update;

    if not found then
      raise exception 'POS_ERROR:OFFER_INVALID';
    end if;
    if v_offer.is_active is not true then
      raise exception 'POS_ERROR:OFFER_INACTIVE';
    end if;
    if v_offer.discount_type <> 'PERCENTAGE' then
      raise exception 'POS_ERROR:OFFER_INVALID';
    end if;
    if v_offer.valid_from is not null and v_offer.valid_from > v_now then
      raise exception 'POS_ERROR:OFFER_NOT_YET_VALID';
    end if;
    if v_offer.valid_to is not null and v_offer.valid_to < v_now then
      raise exception 'POS_ERROR:OFFER_EXPIRED';
    end if;
    if v_offer.franchise_id is not null
       and v_offer.franchise_id is distinct from p_franchise_id then
      raise exception 'POS_ERROR:OFFER_NOT_APPLICABLE';
    end if;

    if v_offer.promotion_id is not null then
      select *
      into v_promotion
      from public.promotions
      where id = v_offer.promotion_id;

      if not found then
        raise exception 'POS_ERROR:PROMOTION_INACTIVE';
      end if;
      if v_promotion.is_active is not true then
        raise exception 'POS_ERROR:PROMOTION_INACTIVE';
      end if;
      if v_promotion.valid_from is not null and v_promotion.valid_from > v_now then
        raise exception 'POS_ERROR:PROMOTION_EXPIRED';
      end if;
      if v_promotion.valid_to is not null and v_promotion.valid_to < v_now then
        raise exception 'POS_ERROR:PROMOTION_EXPIRED';
      end if;
      if not exists (
        select 1
        from public.promotion_franchises pf
        where pf.promotion_id = v_promotion.id
          and pf.franchise_id = p_franchise_id
      ) then
        raise exception 'POS_ERROR:PROMOTION_NOT_APPLICABLE';
      end if;
    end if;

    v_discount_value := v_offer.discount_value;
    v_discount_type := v_offer.discount_type;
    v_offer_name := v_offer.name;
  end if;

  for r in
    select
      (e->>'product_id')::uuid as product_id,
      sum((e->>'quantity')::integer)::integer as quantity
    from jsonb_array_elements(p_items) e
    group by 1
  loop
    if r.quantity > 999 then
      raise exception 'POS_ERROR:INVALID_QUANTITY';
    end if;

    select *
    into v_product
    from public.products
    where id = r.product_id;

    if not found then
      raise exception 'POS_ERROR:UNASSIGNED_PRODUCT';
    end if;

    if v_product.is_active is not true then
      raise exception 'POS_ERROR:INACTIVE_PRODUCT';
    end if;

    if v_product.category_id is not null then
      select *
      into v_category
      from public.product_categories
      where id = v_product.category_id;

      if not found or v_category.is_active is not true then
        raise exception 'POS_ERROR:INACTIVE_CATEGORY';
      end if;
    end if;

    select *
    into v_assignment
    from public.franchise_product_prices
    where franchise_id = p_franchise_id
      and product_id = r.product_id
    for update;

    if not found then
      raise exception 'POS_ERROR:UNASSIGNED_PRODUCT';
    end if;

    if v_assignment.is_active is not true then
      raise exception 'POS_ERROR:INACTIVE_ASSIGNMENT';
    end if;

    v_unit := round(v_assignment.selling_price, 2);
    v_line_total := round(v_unit * r.quantity, 2);
    v_subtotal := v_subtotal + v_line_total;

    v_items_out := v_items_out || jsonb_build_array(
      jsonb_build_object(
        'product_id', r.product_id,
        'product_name_snapshot', v_product.name,
        'unit_price', v_unit,
        'quantity', r.quantity,
        'line_discount_amount', 0,
        'line_total', v_line_total
      )
    );
  end loop;

  if v_discount_value is not null then
    v_discount_amount := round(v_subtotal * v_discount_value / 100, 2);
    if v_discount_amount > v_subtotal then
      v_discount_amount := v_subtotal;
    end if;
  else
    v_discount_amount := 0;
  end if;

  v_taxable := v_subtotal - v_discount_amount;
  if v_taxable < 0 then
    v_taxable := 0;
  end if;

  v_cgst_amount := round(v_taxable * v_cgst_rate / 100, 2);
  v_sgst_amount := round(v_taxable * v_sgst_rate / 100, 2);
  v_gst_amount := v_cgst_amount + v_sgst_amount;
  v_total := v_taxable + v_gst_amount;
  v_order_id := gen_random_uuid();

  for v_attempt in 1..8 loop
    select coalesce(
      max(
        case
          when bill_number ~ '^RS-[0-9]+$'
            then substring(bill_number from 4)::integer
          else 0
        end
      ),
      0
    ) + 1
    into v_seq
    from public.orders
    where franchise_id = p_franchise_id;

    v_bill_number := 'RS-' || lpad(v_seq::text, 4, '0');

    begin
      insert into public.orders (
        id,
        franchise_id,
        bill_number,
        status,
        customer_phone,
        subtotal,
        discount_amount,
        discount_id,
        coupon_id,
        taxable_amount,
        gst_rate,
        gst_amount,
        cgst_rate,
        sgst_rate,
        cgst_amount,
        sgst_amount,
        offer_name,
        discount_type,
        discount_value,
        total_amount,
        payment_method,
        cashier_id,
        completed_at,
        cancelled_at,
        created_at,
        updated_at
      ) values (
        v_order_id,
        p_franchise_id,
        v_bill_number,
        'COMPLETED',
        v_phone,
        v_subtotal,
        v_discount_amount,
        p_offer_id,
        null,
        v_taxable,
        v_gst_rate,
        v_gst_amount,
        v_cgst_rate,
        v_sgst_rate,
        v_cgst_amount,
        v_sgst_amount,
        v_offer_name,
        v_discount_type,
        v_discount_value,
        v_total,
        p_payment_method,
        p_cashier_id,
        v_now,
        null,
        v_now,
        v_now
      );
      exit;
    exception
      when unique_violation then
        if v_attempt = 8 then
          raise exception 'POS_ERROR:BILL_NUMBER_CONFLICT';
        end if;
    end;
  end loop;

  insert into public.order_items (
    order_id,
    product_id,
    product_name_snapshot,
    unit_price,
    quantity,
    line_discount_amount,
    line_total
  )
  select
    v_order_id,
    (item->>'product_id')::uuid,
    item->>'product_name_snapshot',
    (item->>'unit_price')::numeric,
    (item->>'quantity')::integer,
    0,
    (item->>'line_total')::numeric
  from jsonb_array_elements(v_items_out) as item;

  return jsonb_build_object(
    'id', v_order_id,
    'franchise_id', p_franchise_id,
    'bill_number', v_bill_number,
    'status', 'COMPLETED',
    'customer_phone', v_phone,
    'subtotal', v_subtotal,
    'discount_amount', v_discount_amount,
    'discount_id', p_offer_id,
    'offer_id', p_offer_id,
    'offer_name', v_offer_name,
    'discount_type', v_discount_type,
    'discount_value', v_discount_value,
    'discount_percent', v_discount_value,
    'taxable_amount', v_taxable,
    'gst_rate', v_gst_rate,
    'gst_amount', v_gst_amount,
    'cgst_rate', v_cgst_rate,
    'sgst_rate', v_sgst_rate,
    'cgst_amount', v_cgst_amount,
    'sgst_amount', v_sgst_amount,
    'total_amount', v_total,
    'payment_method', p_payment_method,
    'cashier_id', p_cashier_id,
    'cashier_name', v_cashier.full_name,
    'completed_at', v_now,
    'cancelled_at', null,
    'created_at', v_now,
    'updated_at', v_now,
    'franchise_name', v_franchise.name,
    'franchise_address', v_franchise.address,
    'franchise_city', v_franchise.city,
    'franchise_state', v_franchise.state,
    'items', (
      select coalesce(jsonb_agg(to_jsonb(oi) - 'order_id'), '[]'::jsonb)
      from public.order_items oi
      where oi.order_id = v_order_id
    )
  );
end;
$$;

revoke all on function public.complete_pos_order(
  uuid, uuid, text, public.payment_method, text, uuid, jsonb
) from public;
grant execute on function public.complete_pos_order(
  uuid, uuid, text, public.payment_method, text, uuid, jsonb
) to service_role;
