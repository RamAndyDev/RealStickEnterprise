# Architecture

```text
React Browser
   |
   | POST /api/v1/auth/login (email or User ID + password)
   | Supabase Auth session (setSession) + JWT
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

- Staff login uses FastAPI `POST /auth/login`, then `supabase.auth.setSession`. The browser does not query `profiles` to verify passwords.
- Login field placeholder is **Email/User ID**. Admin/Owner use email. Employees use User ID only.
- After 10 minutes of inactivity (mouse, keyboard, touch, pointer, or navigation — not background polling), the client signs out through Supabase Auth and redirects to `/login`.
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
- `SYSTEM_ADMIN` and `FRANCHISE_OWNER` change their own password via `POST /auth/change-password`. The API uses the authenticated profile id and ignores any client-supplied `user_id`. Employees cannot change or recover passwords; the Franchise Owner resets an employee password through Supabase Auth admin update. Passwords are never stored in `public.profiles`.
- Employees have a `profiles.login_id` (User ID) and no business email. Supabase Auth still requires an identity value; the backend uses `{login_id}@employees.invalid` internally and never displays it as an email account.
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

Contact enquiries are emailed with the Resend HTTP API (`RESEND_API_KEY`, `CONTACT_TO_EMAIL`, `CONTACT_FROM_EMAIL`). Enquiry types include General Enquiry, Franchise Enquiry, Complaint, Feedback, and Other. This is not a separate complaints system. Optional public actions (Call / WhatsApp / Email) use `PUBLIC_CONTACT_*` and stay disabled when unset. No `contact_enquiries` table is created.

## Promotions vs Offers

Admin manages **Promotions** (`public.promotions` + `public.promotion_franchises`). Owner manages **Offers** on the existing `public.discounts` table. `discounts.promotion_id` is optional:

- `NULL` — franchise-local offer (independent of Admin)
- set — offer is associated with an Admin promotion; POS availability also requires the promotion to be active, in validity, and to include the employee's franchise

The Admin promotion does not set the franchise discount percentage. Customers never see or enter promo codes. One offer per order remains the M6/M8 rule. GST calculation and completed-order snapshots are unchanged.

Migration `0009` adds `profiles.login_id`, promotions tables, `discounts.promotion_id`, and the `product-images` storage bucket. Migrations `0001`–`0008` are frozen.

POS tablet work is layout-only: AppShell uses a drawer below `lg` on `/pos`, the cart stacks under the product grid below `lg`, and touch targets are enlarged. Checkout, GST, offers, bill numbering, and thermal receipt CSS are unchanged.

Future optimization only (not implemented): an index on `orders (status, completed_at)` may help when completed-bill volume grows. Existing franchise/status indexes are sufficient for the current POC scale.

## Franchise Operational Audit (M11)

A completed audit is an immutable operational inspection of a franchise. It is not a system audit log, activity history, quality score, or draft/submit workflow.

Data model (migration `0010` only; `0001`–`0009` unchanged):

- `franchise_audit_status` enum: `PASS`, `NEEDS_ATTENTION`, `FAIL`
- `franchise_audits` — franchise, audit date, overall status, remarks, plus `franchise_name_snapshot` and `auditor_name_snapshot`
- `franchise_audit_items` — snapshotted `checklist_item` text, `item_key`, `display_order`, status, remarks
- RLS enabled; no anon/authenticated policies. FastAPI uses the service role.

Legacy `quality_audits` / `quality_audit_items` from migration `0001` are unused and untouched.

Authorization:

- `SYSTEM_ADMIN` can list, create, and view audits for every franchise
- `FRANCHISE_OWNER` is scoped to `profile.franchise_id` on list, create, and detail
- `EMPLOYEE` has no navigation, no routes, and receives 403 from `/api/v1/audits`
- Owner detail access to another franchise returns `404 Audit not found`

The 10-item checklist is a backend constant (`FRANCHISE_OPERATIONAL_CHECKLIST`), not a database table. The frontend may mirror the labels; the server validates keys, rejects extras/duplicates, and stores the canonical item text at create time.

`overall_status` is calculated server-side (FAIL if any item is FAIL; else NEEDS_ATTENTION if any item needs attention; else PASS). Historical list/detail views use snapshots only — later franchise or profile renames do not change old audits.

Create is one atomic operation: parent row plus all 10 items. There is no PATCH, DELETE, draft, scheduling, attachments, scoring, or analytics.
