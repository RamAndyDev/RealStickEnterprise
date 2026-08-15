-- M6 business correction: configurable GST, CGST/SGST 50-50 split,
-- basic percentage offers, discount-before-GST, and order snapshots.
-- Does not alter 0001–0005. Does not add inventory/recipe/application tables.

-- ---------------------------------------------------------------------------
-- GST: keep a single total rate in gst_settings. Tighten to a sensible max.
-- CGST/SGST are derived (rate / 2); they are never independently stored here.
-- ---------------------------------------------------------------------------

do $$
declare
  r record;
begin
  for r in
    select c.conname
    from pg_constraint c
    join pg_class t on t.oid = c.conrelid
    join pg_namespace n on n.oid = t.relnamespace
    where n.nspname = 'public'
      and t.relname = 'gst_settings'
      and c.contype = 'c'
      and pg_get_constraintdef(c.oid) ilike '%rate%'
  loop
    execute format('alter table public.gst_settings drop constraint %I', r.conname);
  end loop;
end $$;

alter table public.gst_settings
  add constraint gst_settings_rate_check
    check (rate >= 0 and rate <= 40);

alter table public.gst_settings enable row level security;

-- ---------------------------------------------------------------------------
-- Offers: reuse public.discounts as the M6 Offer model.
-- Global offers have franchise_id null (prototype/business default).
-- ---------------------------------------------------------------------------

alter table public.discounts
  add column if not exists discount_type text not null default 'PERCENTAGE';

do $$
declare
  r record;
begin
  for r in
    select c.conname
    from pg_constraint c
    join pg_class t on t.oid = c.conrelid
    join pg_namespace n on n.oid = t.relnamespace
    where n.nspname = 'public'
      and t.relname = 'discounts'
      and c.contype = 'c'
      and pg_get_constraintdef(c.oid) ilike '%percentage%'
  loop
    execute format('alter table public.discounts drop constraint %I', r.conname);
  end loop;
end $$;

alter table public.discounts rename column percentage to discount_value;
alter table public.discounts rename column valid_until to valid_to;

alter table public.discounts
  add constraint discounts_discount_value_check
    check (discount_value > 0 and discount_value <= 100);

alter table public.discounts
  add constraint discounts_discount_type_check
    check (discount_type = 'PERCENTAGE');

-- ---------------------------------------------------------------------------
-- Order snapshots: CGST/SGST rates + amounts, and offer fields used at sale.
-- Historical receipts must not depend on the live gst_settings or offer row.
-- ---------------------------------------------------------------------------

alter table public.orders
  add column if not exists cgst_rate numeric(5, 2) not null default 0
    check (cgst_rate >= 0 and cgst_rate <= 100),
  add column if not exists sgst_rate numeric(5, 2) not null default 0
    check (sgst_rate >= 0 and sgst_rate <= 100),
  add column if not exists cgst_amount numeric(12, 2) not null default 0
    check (cgst_amount >= 0),
  add column if not exists sgst_amount numeric(12, 2) not null default 0
    check (sgst_amount >= 0),
  add column if not exists offer_name text,
  add column if not exists discount_type text,
  add column if not exists discount_value numeric(5, 2)
    check (discount_value is null or (discount_value > 0 and discount_value <= 100));

-- Backfill CGST/SGST from the existing GST snapshot.
-- Use remainder assignment so:
--   cgst_rate + sgst_rate = gst_rate
--   cgst_amount + sgst_amount = gst_amount
-- Equal 50/50 halves are used when gst_rate splits evenly at 2 d.p. (e.g. 5.00).
-- If a historical rate cannot split evenly (e.g. 5.01), do NOT set both halves to
-- round(rate/2, 2) — that would make 2.51 + 2.51 = 5.02. Instead assign the
-- remainder to SGST so the stored gst_rate/gst_amount stay authoritative.
update public.orders
set
  cgst_rate = round(gst_rate / 2, 2),
  sgst_rate = gst_rate - round(gst_rate / 2, 2),
  cgst_amount = round(gst_amount / 2, 2),
  sgst_amount = gst_amount - round(gst_amount / 2, 2);

do $$
declare
  uneven integer;
begin
  select count(*)
  into uneven
  from public.orders
  where round(gst_rate / 2, 2) * 2 <> gst_rate;

  if uneven > 0 then
    raise notice
      '0006: % historical order(s) have a GST rate that cannot split into equal CGST/SGST at 2 decimal places. CGST/SGST halves differ by 0.01 so their sum still equals the original gst_rate.',
      uneven;
  end if;
end $$;

alter table public.orders
  add constraint orders_cgst_sgst_sum_check
    check (cgst_amount + sgst_amount = gst_amount);

alter table public.orders
  add constraint orders_cgst_sgst_rate_sum_check
    check (cgst_rate + sgst_rate = gst_rate);

-- ---------------------------------------------------------------------------
-- Atomic checkout: offer_id (not client discount %), CGST/SGST, snapshots.
-- Signature change requires DROP of the 0004/0005 numeric-discount overload.
-- ---------------------------------------------------------------------------

drop function if exists public.complete_pos_order(
  uuid, uuid, text, public.payment_method, text, numeric, jsonb
);

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

revoke all on function public.complete_pos_order(
  uuid, uuid, text, public.payment_method, text, uuid, jsonb
) from anon, authenticated;

grant execute on function public.complete_pos_order(
  uuid, uuid, text, public.payment_method, text, uuid, jsonb
) to service_role;
