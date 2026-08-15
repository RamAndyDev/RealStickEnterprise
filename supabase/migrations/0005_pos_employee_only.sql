-- POS cashier role: EMPLOYEE only (FRANCHISE_OWNER and SYSTEM_ADMIN are denied).
-- Recreates public.complete_pos_order from 0004 with the tightened role check.
-- Does not change pricing, GST, bill numbers, or order persistence.


create or replace function public.complete_pos_order(
  p_franchise_id uuid,
  p_cashier_id uuid,
  p_cashier_role text,
  p_payment_method public.payment_method,
  p_customer_phone text,
  p_discount_percent numeric,
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
  v_gst_rate numeric(5, 2);
  v_discount_percent numeric(5, 2);
  v_subtotal numeric(12, 2) := 0;
  v_discount_amount numeric(12, 2) := 0;
  v_taxable numeric(12, 2) := 0;
  v_gst_amount numeric(12, 2) := 0;
  v_total numeric(12, 2) := 0;
  v_seq integer;
  v_bill_number text;
  v_order_id uuid;
  v_now timestamptz := now();
  v_item jsonb;
  v_product_id uuid;
  v_qty numeric;
  v_qty_int integer;
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

  v_discount_percent := coalesce(p_discount_percent, 0);
  if v_discount_percent < 0 or v_discount_percent > 100 then
    raise exception 'POS_ERROR:INVALID_DISCOUNT';
  end if;
  if p_cashier_role <> 'FRANCHISE_OWNER' and v_discount_percent <> 0 then
    raise exception 'POS_ERROR:DISCOUNT_NOT_ALLOWED';
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

  v_discount_amount := round(v_subtotal * v_discount_percent / 100, 2);
  v_taxable := v_subtotal - v_discount_amount;
  v_gst_amount := round(v_taxable * v_gst_rate / 100, 2);
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
        null,
        null,
        v_taxable,
        v_gst_rate,
        v_gst_amount,
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
    'discount_percent', v_discount_percent,
    'taxable_amount', v_taxable,
    'gst_rate', v_gst_rate,
    'gst_amount', v_gst_amount,
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
  uuid, uuid, text, public.payment_method, text, numeric, jsonb
) from public;

revoke all on function public.complete_pos_order(
  uuid, uuid, text, public.payment_method, text, numeric, jsonb
) from anon, authenticated;

grant execute on function public.complete_pos_order(
  uuid, uuid, text, public.payment_method, text, numeric, jsonb
) to service_role;
