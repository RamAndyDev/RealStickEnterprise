-- Observation #3 final: franchise selling price is independent of master price.
-- Replaces function bodies only. Does not modify 0007, 0011, tables, columns,
-- RLS, triggers, or existing franchise_product_prices / products.price data.
-- Rule: selling_price IS NOT NULL AND selling_price > 0.
-- Master price is reference-only and must not constrain franchise selling prices.

create or replace function public.enforce_franchise_selling_price()
returns trigger
language plpgsql
as $$
begin
  if new.selling_price is null or new.selling_price <= 0 then
    raise exception 'Selling price must be greater than 0';
  end if;

  return new;
end;
$$;

create or replace function public.enforce_master_price_above_selling()
returns trigger
language plpgsql
as $$
begin
  -- Master price is independent of franchise selling prices.
  -- Changing products.price must not inspect or constrain franchise_product_prices.
  return new;
end;
$$;
