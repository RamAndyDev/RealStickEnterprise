# Initial API Contract

Base: `/api/v1`

## Public
- GET `/health`
- GET `/health/database` — verifies Supabase connectivity (503 when unavailable)

## Auth (Bearer access token from Supabase Auth)
- POST `/auth/login` — staff sign-in. Body: `{ "identifier", "password" }`
  - `SYSTEM_ADMIN` / `FRANCHISE_OWNER`: `identifier` is the business email
  - `EMPLOYEE`: `identifier` is the User ID (for example `EMP001`). Employees have no business email
  - The backend resolves User ID to the employee's Supabase Auth identity and performs a password grant. The frontend never queries `profiles` to verify passwords
  - Employee login with an email (including the internal `*@employees.invalid` identity) is rejected
  - Success returns `{ access_token, refresh_token, token_type, expires_in }`. Passwords are never returned
- GET `/auth/me` — authenticated profile (role/franchise from `public.profiles`)
  - Includes `login_id` for employees
  - Employee `email` is always `null`. Admin/Owner email is the Supabase Auth email
- POST `/auth/change-password` — `SYSTEM_ADMIN` and `FRANCHISE_OWNER` only
  - Body: `{ "new_password": "..." }` (min 8 characters)
  - Uses the authenticated profile id only; a client-supplied `user_id` is ignored
  - Password is stored in Supabase Auth. It is never written to `public.profiles` and never returned
  - `EMPLOYEE` receives 403. Franchise Owner resets employee passwords instead
- Inactivity logout is a frontend session UX (10 minutes of no mouse/keyboard/touch/navigation). Backend JWT validation is unchanged

## Temporary auth verification endpoints (remove later)
- GET `/auth/test/admin` — `SYSTEM_ADMIN` only
- GET `/auth/test/owner` — `FRANCHISE_OWNER` only
- GET `/auth/test/employee` — `EMPLOYEE` only
- GET `/auth/test/franchise/{franchise_id}` — franchise-scoped access check

## Admin franchises (SYSTEM_ADMIN only)
- GET `/admin/franchises`
- GET `/admin/franchises/{id}`
- POST `/admin/franchises`
- PATCH `/admin/franchises/{id}`
- PATCH `/admin/franchises/{id}/status`
- PATCH `/admin/franchises/{id}/owner`
- POST `/admin/franchises/{id}/owners` — create Auth user + FRANCHISE_OWNER profile (invite/recovery password setup)
- GET `/admin/franchises/{id}/launch-checklist`
- PATCH `/admin/franchises/{id}/launch-checklist/{item_id}`
- GET `/admin/franchise-applications`
- GET `/admin/franchise-applications/{id}`

## POS checkout (EMPLOYEE only)
- GET `/pos/menu`
- GET `/pos/offers`
- POST `/pos/orders` — atomic checkout; allocates bill number; persists snapshots
- GET `/pos/orders/{order_id}` — employee reprint of a completed bill in their franchise

Owner and System Admin receive 403 on all `/pos` endpoints. Checkout behavior is frozen.

## Completed bills / order history (read-only)
Authenticated `EMPLOYEE`, `FRANCHISE_OWNER`, and `SYSTEM_ADMIN`.

- GET `/orders` — completed bills only (`status=COMPLETED`)
  - Query: `franchise_id`, `bill_number`, `payment_method` (`CASH`|`UPI`|`CARD`), `from_date`, `to_date`, `page`, `page_size`
  - Defaults: `page=1`, `page_size=20` (max 100)
  - Employee/Owner: `franchise_id` is taken from the authenticated profile; a client-supplied value is ignored
  - System Admin: optional `franchise_id`; omit it to page across all franchises (franchise name is included on each row)
- GET `/orders/{order_id}` — read-only bill detail with stored order/order_item snapshots

These endpoints never create, update, cancel, or recalculate orders. Historical GST, CGST/SGST, offer/discount, product name, and unit price come from the original snapshots.

Cross-franchise access by Employee/Owner returns 404 (`Order not found`).

Thermal reprint reuses `/print/receipt/{orderId}` and GET `/orders/{order_id}` (same `order_id` / `bill_number`).

## Reports and dashboards (read-only)

Authenticated `SYSTEM_ADMIN` and `FRANCHISE_OWNER` only for management reports and dashboards. `EMPLOYEE` receives 403 on those endpoints. Unauthenticated requests receive 401.

All aggregations use `orders.status = COMPLETED` only. DRAFT and CANCELLED orders are excluded.

Historical values come from completed-order snapshots (`orders.total_amount`, `order_items.product_name_snapshot`, `unit_price`, `quantity`, `line_total`). Live product prices, franchise selling prices, GST, and offers are never reapplied.

Scope:
- `SYSTEM_ADMIN` — all franchises. A client-supplied `franchise_id` is ignored.
- `FRANCHISE_OWNER` — `profile.franchise_id` only. A client-supplied `franchise_id` is ignored and cannot widen scope.

Date periods (`period`) use the same UTC calendar-day semantics as M7 bill filters:
- `today`
- `7d` — today and the previous 6 days
- `30d` — today and the previous 29 days

Default `period` is `7d`.

- GET `/reports/summary`
  - Query: `period`
  - Returns `revenue` (`SUM(orders.total_amount)`), `orders` (completed count), `avg_order` (revenue / orders, nearest rupee, or 0), `items_sold` (`SUM(order_items.quantity)`), and up to 5 `recent_bills` for the existing bill-detail route
- GET `/reports/daily`
  - Query: `period`
  - Returns a daily revenue series. Today is 1 day. Last 7 / Last 30 days return at most 7 bars (POC). Missing days are 0.
- GET `/reports/products`
  - Query: `period`
  - Top 8 products by snapshot line revenue (`unit_price × quantity`), using `product_name_snapshot`
- GET `/reports/payments`
  - Query: `period`
  - Cash, UPI, and Card totals (`SUM(orders.total_amount)` grouped by `payment_method`). Missing methods return 0.
- GET `/reports/dashboard/admin` — `SYSTEM_ADMIN` only
  - Today: revenue, order count, active outlets (`franchises.status = ACTIVE`), top seller by quantity
  - Outlet performance today (franchise name, revenue, orders)
  - All-time completed revenue and bill count
- GET `/reports/dashboard/owner` — `FRANCHISE_OWNER` only
  - Today: revenue, bill count, top product by quantity
  - All-time revenue for the authenticated franchise
  - Up to 8 of today's bills (`id` is the existing `/bills/:orderId` route)

These endpoints never create, update, cancel, export, or recalculate orders.

## Employee Daily Sales (EMPLOYEE only)

- GET `/reports/employee/daily` — completed billing for one UTC calendar day for the authenticated employee's franchise
  - Query: `date` (`YYYY-MM-DD`). Default: today (UTC). One calendar day only.
  - Future dates are rejected (422). Invalid date format is rejected (422).

Authorization:
- `EMPLOYEE` — own `profile.franchise_id` only
- `SYSTEM_ADMIN` / `FRANCHISE_OWNER` — 403
- Unauthenticated — 401

A client-supplied `franchise_id` is ignored and cannot widen scope.

Uses the same UTC calendar-day filter as M7/M9 (`completed_at` for the selected day). Only `orders.status = COMPLETED` are included.

Server-side aggregation:
- `summary.revenue` = `SUM(orders.total_amount)`
- `summary.bills` = completed order count
- `summary.items_sold` = `SUM(order_items.quantity)`
- `summary.average_bill` = revenue / bills, nearest rupee, or 0 when there are no bills
- `payments.cash` / `upi` / `card` = `SUM(orders.total_amount)` grouped by `payment_method`
- `bills` = completed bills for the selected date (`id` is the existing `/bills/:orderId` route)

Historical values come from completed-order snapshots. Live product prices, GST, and offers are never reapplied. Empty days return zeros and an empty bills list.

## Public website (no JWT)

Anonymous visitors may call these endpoints. They do **not** use admin, owner, or POS APIs.

Responses are explicit whitelists. They never include prices, SKU, metadata, franchise assignment, GST, offers, or staff identity.

- GET `/public/categories` — active product categories (`id`, `name`, `display_order`)
- GET `/public/products` — active products in active categories (`id`, `category_id`, `category_name`, `name`, `description`, `image_url`)
  - `product.is_active = true` AND `product_categories.is_active = true` AND `product.category_id IS NOT NULL`
  - Franchise assignment is not required
  - Uncategorized and inactive items are omitted
- GET `/public/gallery` — approved, non-archived gallery items sorted by `display_order`, then `created_at`
  - Whitelist: `id`, `title`, `caption`, `author_name`, `media_type`, `media_url`, `display_order`
  - Never returns `uploaded_by`, `storage_path`, `franchise_id`, or approval/archive flags
- GET `/public/contact-options` — configured public contact actions (`phone`, `whatsapp`, `email`, and matching `tel:` / `wa.me` / `mailto` URLs). Missing values are `null`; the API never invents numbers
- POST `/public/contact` — send a website enquiry to the RealStick team via Resend
  - Body: `{ "name", "phone", "email", "message", "enquiry_type?", "website?" }`
  - `enquiry_type`: `GENERAL` | `FRANCHISE` | `COMPLAINT` | `FEEDBACK` | `OTHER` (default `GENERAL`)
  - `website` is a honeypot; a non-empty value is rejected
  - Success: `{ "message": "Thank you. The RealStick team will contact you." }`
  - Delivery failure (missing config, invalid key, or Resend error): 502 `{ "detail": "Unable to send your enquiry right now. Please try again." }` — never a success payload
  - Does **not** create `franchise_applications` rows
  - Rate limit: 5 requests / hour / IP
  - There is no public promotions, coupons, or offer endpoint

## Promotions (SYSTEM_ADMIN) and Offers (FRANCHISE_OWNER)

Customers never enter promo codes. Promotions are internal business controls.

- GET/POST `/admin/promotions` — list/create Admin promotions (`name`, `description`, `promo_code`, validity, `is_active`, `franchise_ids`)
- PATCH `/admin/promotions/{id}` — edit, activate/deactivate, change participating franchises
- GET `/owner/promotions` — promotions that include the owner's franchise (read-only)
- GET/POST `/owner/offers` — franchise-local offers. `promotion_id` is optional (`null` = independent local offer)
- PATCH `/owner/offers/{id}` — owner may edit/activate only their own franchise offers
- GET `/pos/offers` — applicable offers for the authenticated employee's franchise
  - Offer is shown when it is active, in validity, belongs to the franchise, and either has no promotion or the linked promotion is active, in validity, and includes the franchise
  - Employee selects an offer; they never enter a promo code
  - One offer per order remains enforced at checkout
  - Existing M6/M8 GST path is unchanged: subtotal → offer discount → taxable → CGST/SGST → total
  - Completed-order offer snapshots are not rewritten when a promotion later changes

`GET/POST/PATCH /admin/offers` remains for existing GST/POS test and service compatibility. Admin UI uses Promotions; Owner UI uses Offers & Discounts.

## Employees (FRANCHISE_OWNER)

- GET/POST `/owner/employees` — list/create employees for the authenticated franchise
  - Create body: `{ "login_id", "full_name", "password", "confirm_password?", "phone?" }`
  - No email field. An internal Auth identity (`{login_id}@employees.invalid`) is an implementation detail and is never shown
- PATCH `/owner/employees/{id}` — name, User ID, phone, active status
- POST `/owner/employees/{id}/reset-password` — `{ "new_password", "confirm_password" }` updates Supabase Auth. No recovery email is sent
- Admin User Management (`/admin/users`) continues to list only `SYSTEM_ADMIN` and `FRANCHISE_OWNER`. Email is hydrated from Supabase Auth and is read-only. Employees are excluded

## Admin gallery (SYSTEM_ADMIN only)

Owner and Employee receive 403.

- GET `/admin/gallery`
- POST `/admin/gallery` — IMAGE (draft until media upload), VIDEO (HTTPS URL), TESTIMONIAL (caption + author_name)
- PATCH `/admin/gallery/{id}` — title, caption, author, display_order, media_url (video), `is_approved`, `is_archived`
- POST `/admin/gallery/{id}/media` — JPEG/PNG/WEBP upload to the `gallery` storage bucket

Brand-level items use `franchise_id = NULL`. Prefer archive (`is_archived`) over hard delete.

## Environment (server-side only)

- `RESEND_API_KEY`
- `CONTACT_TO_EMAIL`
- `CONTACT_FROM_EMAIL`
- `PUBLIC_CONTACT_PHONE` (optional)
- `PUBLIC_CONTACT_WHATSAPP` (optional; digits used for `https://wa.me/{digits}`)
- `PUBLIC_CONTACT_EMAIL` (optional)

Never expose these, the Supabase service-role key, or passwords to the React app.

Planned resources (not in this milestone):
- `/inventory`
- `/audits`
- `/coupons`
- franchise applications
