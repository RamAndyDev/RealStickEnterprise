# Architecture

```text
React Browser
   |
   | Supabase Auth (email/password session + JWT)
   | HTTPS / JSON + Authorization: Bearer <access_token>
   v
FastAPI
   |
   +--> JWT validation (Supabase JWKS / ES256)
   +--> Load public.profiles (service role)
   +--> Role / franchise authorization
   +--> Feature Service
   +--> Repository
   v
Supabase PostgreSQL
```

## Frontend
`src/app`, `src/components`, `src/features`, `src/lib`, `src/types`

- Browser talks to Supabase Auth with the **anon** key only.
- Application authorization is enforced by FastAPI using the verified JWT + profile.

## Backend
`app/core`, `app/db`, `app/modules`

Auth dependencies:
- `get_current_user()`
- `get_current_profile()`
- `require_role(...)`
- `require_franchise_access(...)`

## POS transaction invariant
1. Validate outlet/product state.
2. Validate price/discount/offer rules.
3. Calculate subtotal / GST (CGST + SGST) / total server-side.
4. Persist the completed order and order-item snapshots atomically.
5. Allocate a franchise-scoped bill number.
6. Commit.

The browser total is only a preview; the backend is authoritative.

Inventory consumption, recipe deduction, and franchise applications are **out of scope** for the current billing MVP. They are not performed during POS checkout.

Completed bills are immutable snapshots. Later GST, offer, product, or selling-price changes do not alter historical orders.

## Completed bills (M7)
Read-only history sits on `public.orders` / `public.order_items`.

- List/search/filter/paginate via `GET /api/v1/orders`
- Detail via `GET /api/v1/orders/{order_id}`
- Reprint reuses the existing thermal receipt at `/print/receipt/{orderId}`
- Employee and Franchise Owner are scoped to `profile.franchise_id`
- System Admin selects a franchise (or pages across all franchises with franchise name on each row)

POS checkout (`POST /api/v1/pos/orders`) remains employee-only and is unchanged.

## Reports and dashboards (M9)

Read-only aggregation sits on `public.orders` / `public.order_items` / `public.franchises`. No report tables, materialized views, or M9 migration were added.

- `SYSTEM_ADMIN` sees all-franchise totals. Reports do not take a franchise selector.
- `FRANCHISE_OWNER` is scoped to `profile.franchise_id`.
- `EMPLOYEE` is rejected by management `/reports` and dashboard endpoints.
- `EMPLOYEE` Daily Sales (`GET /reports/employee/daily`) is a single-day operational view scoped to `profile.franchise_id`. Optional `date=YYYY-MM-DD` selects a past or current UTC day (default today). Future dates are rejected. Admin and Owner cannot use it.
- Authenticated users change their own password via `POST /auth/change-password`. The API uses the authenticated profile id and ignores any client-supplied `user_id`. Employee navigation exposes Change Password; Admin/Owner password-reset flows are unchanged.
- Revenue = `SUM(orders.total_amount)` for completed orders. Average order = revenue / orders, rounded to the nearest rupee.
- Product rankings use snapshot `product_name_snapshot` and `unit_price × quantity`. Order-level discount and GST are not allocated to products.
- Admin "Active Outlets" = `COUNT(franchises) WHERE status = ACTIVE`, including outlets with zero sales.
- Admin "Top Seller Today" / Owner "Top Product Today" = highest `SUM(order_items.quantity)` for completed orders today.
- Date windows reuse M7 UTC start-of-day / next-day filters (`today`, `7d`, `30d`).

## Public website and staff app (M10)

The React SPA hosts two layouts:

- **Public website** (`PublicLayout`): `/`, `/menu`, `/about`, `/gallery`, `/contact`. No login. Anonymous visitors are never redirected to `/login`.
- **Staff / POS** (`AppShell` + `ProtectedRoute`): `/login`, `/dashboard`, `/pos`, `/owner/menu`, and existing staff routes. Unauthenticated staff URLs redirect to `/login`. Wrong-role access redirects to the role landing path (`/dashboard` or `/pos`), never to public `/`.

Staff landing after login:

- `SYSTEM_ADMIN` / `FRANCHISE_OWNER` → `/dashboard`
- `EMPLOYEE` → `/pos`

Owner Menu/Pricing is `/owner/menu`. Public `/menu` is a price-free catalogue. Backend owner APIs remain `GET/PATCH /api/v1/owner/menu`.

Public catalogue and gallery reads go through FastAPI with the service-role key. Anonymous PostgREST access to `products` is not enabled. The previous anon select policy on `gallery_items` was removed in migration `0008`; public gallery reads use `/api/v1/public/gallery`.

Contact enquiries are emailed with the Resend HTTP API (`RESEND_API_KEY`, `CONTACT_TO_EMAIL`, `CONTACT_FROM_EMAIL`). No `contact_enquiries` table is created.

POS tablet work is layout-only: AppShell uses a drawer below `lg` on `/pos`, the cart stacks under the product grid below `lg`, and touch targets are enlarged. Checkout, GST, offers, bill numbering, and thermal receipt CSS are unchanged.

Future optimization only (not implemented): an index on `orders (status, completed_at)` may help when completed-bill volume grows. Existing franchise/status indexes are sufficient for the current POC scale.
