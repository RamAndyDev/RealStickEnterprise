-- M6.1 business-rule enforcement:
-- 1. Atomic category deactivation also deactivates products in that category.
-- 2. Franchise selling price must be > 0 and strictly less than master price.
-- 3. POS checkout requires an active category as well as product + assignment.
-- Does not drop deferred tables.

-- ---------------------------------------------------------------------------
-- Refuse to apply if existing selling prices violate:
--   0 < selling_price < products.price
-- Do NOT modify products.price, selling_price, assignments, or any other data.
-- ---------------------------------------------------------------------------

do $$
declare
  v_above_or_equal_master integer;
  v_not_positive integer;
begin
  select count(*)
  into v_above_or_equal_master
  from public.franchise_product_prices fpp
  inner join public.products p on p.id = fpp.product_id
  where fpp.selling_price >= p.price;

  if v_above_or_equal_master > 0 then
    raise exception
      '0007 cannot be applied: existing franchise selling prices are greater than or equal to their product master prices. Correct these pricing records before applying this migration.';
  end if;

  select count(*)
  into v_not_positive
  from public.franchise_product_prices
  where selling_price is null or selling_price <= 0;

  if v_not_positive > 0 then
    raise exception
      '0007 cannot be applied: existing franchise selling prices must be greater than 0. Correct these pricing records before applying this migration.';
  end if;
end;
$$;

alter table public.franchise_product_prices
  drop constraint if exists franchise_product_prices_selling_price_check;

alter table public.franchise_product_prices
  add constraint franchise_product_prices_selling_price_positive
  check (selling_price > 0);

-- ---------------------------------------------------------------------------
-- Selling price < master price
-- ---------------------------------------------------------------------------

create or replace function public.enforce_franchise_selling_price()
returns trigger
language plpgsql
as $$
declare
  v_master numeric(12, 2);
begin
  if new.selling_price is null or new.selling_price <= 0 then
    raise exception 'Selling price must be greater than 0';
  end if;

  select price
  into v_master
  from public.products
  where id = new.product_id;

  if not found then
    raise exception 'Product not found';
  end if;

  if new.selling_price >= v_master then
    raise exception 'Selling price must be strictly less than the master price';
  end if;

  return new;
end;
$$;

drop trigger if exists trg_franchise_selling_price on public.franchise_product_prices;

create trigger trg_franchise_selling_price
before insert or update of selling_price, product_id
on public.franchise_product_prices
for each row
execute procedure public.enforce_franchise_selling_price();

create or replace function public.enforce_master_price_above_selling()
returns trigger
language plpgsql
as $$
begin
  if new.price is distinct from old.price then
    if exists (
      select 1
      from public.franchise_product_prices fpp
      where fpp.product_id = new.id
        and fpp.is_active is true
        and fpp.selling_price >= new.price
    ) then
      raise exception 'Master price cannot be reduced below existing franchise selling prices.';
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists trg_master_price_above_selling on public.products;

create trigger trg_master_price_above_selling
before update of price
on public.products
for each row
execute procedure public.enforce_master_price_above_selling();

-- ---------------------------------------------------------------------------
-- Atomic category activation / deactivation
-- Deactivating a category inactivates all products in that category.
-- Reactivating a category does NOT reactivate those products.
-- ---------------------------------------------------------------------------

create or replace function public.set_product_category_active(
  p_category_id uuid,
  p_is_active boolean
)
returns public.product_categories
language plpgsql
security definer
set search_path = public
as $$
declare
  v_category public.product_categories;
begin
  update public.product_categories
  set
    is_active = p_is_active,
    updated_at = now()
  where id = p_category_id
  returning * into v_category;

  if not found then
    raise exception 'CATEGORY_NOT_FOUND';
  end if;

  if p_is_active is not true then
    update public.products
    set
      is_active = false,
      updated_at = now()
    where category_id = p_category_id
      and is_active is true;
  end if;

  return v_category;
end;
$$;

revoke all on function public.set_product_category_active(uuid, boolean) from public;
revoke all on function public.set_product_category_active(uuid, boolean) from anon, authenticated;
grant execute on function public.set_product_category_active(uuid, boolean) to service_role;

-- ---------------------------------------------------------------------------
-- POS checkout: category must also be active
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

revoke all on function public.complete_pos_order(
  uuid, uuid, text, public.payment_method, text, uuid, jsonb
) from anon, authenticated;

grant execute on function public.complete_pos_order(
  uuid, uuid, text, public.payment_method, text, uuid, jsonb
) to service_role;
