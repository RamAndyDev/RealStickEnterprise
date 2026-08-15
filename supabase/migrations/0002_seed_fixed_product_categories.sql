-- Seed the five fixed RealStick product categories (system reference data).
-- Idempotent: safe to re-run; does not insert products or demo data.
-- Exact names from RealStick_POS.html prototype menus.

insert into public.product_categories (name, display_order, is_active)
values
  ('Zest Collection', 1, true),
  ('Garden Collection', 2, true),
  ('Harvest Collection', 3, true),
  ('The Reserve', 4, true),
  ('Kulfi Heritage', 5, true)
on conflict (name) do nothing;
