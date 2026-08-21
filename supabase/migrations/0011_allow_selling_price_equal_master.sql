-- Observation #3 follow-up: franchise selling price may equal master price.
-- Replaces function bodies only. Does not modify 0007, tables, columns, RLS, or triggers.
-- Rule: 0 < selling_price <= products.price

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

  if new.selling_price > v_master then
    raise exception 'Selling price must not exceed the master price';
  end if;

  return new;
end;
$$;

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
        and fpp.selling_price > new.price
    ) then
      raise exception 'Master price cannot be reduced below existing franchise selling prices.';
    end if;
  end if;
  return new;
end;
$$;
