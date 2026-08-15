"""In-memory equivalent of public.complete_pos_order (used by FakeDatabase tests).

Production checkout is the PostgreSQL function in
0007_business_rules.sql (extends 0006_configurable_gst_and_basic_offers.sql).
Keep the validation and money rules aligned with that function.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID, uuid4

from app.core.gst import split_gst_rate

TWOPLACES = Decimal('0.01')
MAX_QTY = 999
MAX_LINES = 100
ALLOWED_PAYMENTS = frozenset({'CASH', 'UPI', 'CARD'})
ALLOWED_ROLES = frozenset({'EMPLOYEE'})


class PosCheckoutError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _as_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _find(rows: list[dict], **eq: object) -> dict | None:
    for row in rows:
        if all(str(row.get(key)) == str(val) for key, val in eq.items()):
            return row
    return None


def _parse_dt(value: object) -> datetime | None:
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).replace('Z', '+00:00')
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def complete_pos_order_atomic(tables: dict[str, list[dict]], params: dict[str, Any]) -> dict[str, Any]:
    franchise_id = params.get('p_franchise_id')
    cashier_id = params.get('p_cashier_id')
    cashier_role = str(params.get('p_cashier_role') or '')
    payment_method = params.get('p_payment_method')
    customer_phone = params.get('p_customer_phone')
    offer_id = params.get('p_offer_id')
    items_in = params.get('p_items')
    now_dt = datetime.now(timezone.utc)

    if not franchise_id:
        raise PosCheckoutError('FRANCHISE_NOT_FOUND')

    franchise = _find(tables.get('franchises', []), id=franchise_id)
    if not franchise:
        raise PosCheckoutError('FRANCHISE_NOT_FOUND')

    cashier = _find(tables.get('profiles', []), id=cashier_id)
    if not cashier or not cashier.get('is_active'):
        raise PosCheckoutError('CASHIER_INVALID')
    if str(cashier.get('franchise_id')) != str(franchise_id):
        raise PosCheckoutError('FRANCHISE_MISMATCH')
    if cashier.get('role') != 'EMPLOYEE':
        raise PosCheckoutError('ROLE_NOT_ALLOWED')
    if cashier_role not in ALLOWED_ROLES:
        raise PosCheckoutError('ROLE_NOT_ALLOWED')

    if payment_method not in ALLOWED_PAYMENTS:
        raise PosCheckoutError('INVALID_PAYMENT')

    phone = None
    if isinstance(customer_phone, str):
        stripped = customer_phone.strip()
        phone = stripped or None

    if not isinstance(items_in, list) or not items_in:
        raise PosCheckoutError('EMPTY_CART')
    if len(items_in) > MAX_LINES:
        raise PosCheckoutError('CART_TOO_LARGE')

    merged: dict[str, int] = {}
    order_keys: list[str] = []
    for raw in items_in:
        if not isinstance(raw, dict) or not raw.get('product_id'):
            raise PosCheckoutError('INVALID_ITEM')
        try:
            UUID(str(raw['product_id']))
        except (ValueError, TypeError, AttributeError) as exc:
            raise PosCheckoutError('INVALID_ITEM') from exc
        qty_raw = raw.get('quantity')
        if isinstance(qty_raw, bool) or not isinstance(qty_raw, (int, float, Decimal)):
            raise PosCheckoutError('INVALID_QUANTITY')
        qty_dec = Decimal(str(qty_raw))
        if qty_dec != qty_dec.to_integral_value() or qty_dec < 1 or qty_dec > MAX_QTY:
            raise PosCheckoutError('INVALID_QUANTITY')
        qty = int(qty_dec)
        key = str(raw['product_id'])
        if key not in merged:
            order_keys.append(key)
            merged[key] = 0
        merged[key] += qty
        if merged[key] > MAX_QTY:
            raise PosCheckoutError('INVALID_QUANTITY')

    gst_row = next(
        (row for row in tables.get('gst_settings', []) if row.get('is_active')),
        None,
    )
    if gst_row is None or gst_row.get('rate') is None:
        raise PosCheckoutError('GST_UNAVAILABLE')
    try:
        gst_rate = _money(gst_row['rate'])
        cgst_rate, sgst_rate = split_gst_rate(gst_rate)
    except Exception as exc:
        raise PosCheckoutError('GST_UNAVAILABLE') from exc

    offer_name = None
    discount_type = None
    discount_value: Decimal | None = None
    offer_id_str = None
    if offer_id not in (None, ''):
        offer = _find(tables.get('discounts', []), id=offer_id)
        if not offer:
            raise PosCheckoutError('OFFER_INVALID')
        if not offer.get('is_active'):
            raise PosCheckoutError('OFFER_INACTIVE')
        if str(offer.get('discount_type') or 'PERCENTAGE') != 'PERCENTAGE':
            raise PosCheckoutError('OFFER_INVALID')
        valid_from = _parse_dt(offer.get('valid_from'))
        valid_to = _parse_dt(offer.get('valid_to'))
        if valid_from and valid_from > now_dt:
            raise PosCheckoutError('OFFER_NOT_YET_VALID')
        if valid_to and valid_to < now_dt:
            raise PosCheckoutError('OFFER_EXPIRED')
        offer_franchise = offer.get('franchise_id')
        if offer_franchise not in (None, '') and str(offer_franchise) != str(franchise_id):
            raise PosCheckoutError('OFFER_NOT_APPLICABLE')
        try:
            discount_value = _money(offer['discount_value'])
        except Exception as exc:
            raise PosCheckoutError('OFFER_INVALID') from exc
        if discount_value <= 0 or discount_value > 100:
            raise PosCheckoutError('OFFER_INVALID')
        offer_name = offer.get('name')
        discount_type = str(offer.get('discount_type') or 'PERCENTAGE')
        offer_id_str = str(offer['id'])

    built_items: list[dict[str, Any]] = []
    subtotal = Decimal('0.00')
    products = tables.get('products', [])
    assignments = tables.get('franchise_product_prices', [])

    for product_id in order_keys:
        quantity = merged[product_id]
        product = _find(products, id=product_id)
        if not product:
            raise PosCheckoutError('UNASSIGNED_PRODUCT')
        if not product.get('is_active'):
            raise PosCheckoutError('INACTIVE_PRODUCT')
        category_id = product.get('category_id')
        if category_id:
            category = _find(tables.get('product_categories', []), id=category_id)
            if not category or not category.get('is_active'):
                raise PosCheckoutError('INACTIVE_CATEGORY')
        assignment = next(
            (
                row
                for row in assignments
                if str(row.get('franchise_id')) == str(franchise_id)
                and str(row.get('product_id')) == product_id
            ),
            None,
        )
        if not assignment:
            raise PosCheckoutError('UNASSIGNED_PRODUCT')
        if not assignment.get('is_active'):
            raise PosCheckoutError('INACTIVE_ASSIGNMENT')

        unit_price = _money(assignment['selling_price'])
        line_total = _money(unit_price * quantity)
        subtotal += line_total
        built_items.append(
            {
                'product_id': product_id,
                'product_name_snapshot': product['name'],
                'unit_price': unit_price,
                'quantity': quantity,
                'line_discount_amount': Decimal('0.00'),
                'line_total': line_total,
            }
        )

    if discount_value is not None:
        discount_amount = _money(subtotal * discount_value / Decimal('100'))
        if discount_amount > subtotal:
            discount_amount = subtotal
    else:
        discount_amount = Decimal('0.00')

    taxable = subtotal - discount_amount
    if taxable < 0:
        taxable = Decimal('0.00')

    cgst_amount = _money(taxable * cgst_rate / Decimal('100'))
    sgst_amount = _money(taxable * sgst_rate / Decimal('100'))
    gst_amount = cgst_amount + sgst_amount
    total = taxable + gst_amount

    orders = tables.setdefault('orders', [])
    seq = 0
    for existing in orders:
        if str(existing.get('franchise_id')) != str(franchise_id):
            continue
        bill = str(existing.get('bill_number') or '')
        if bill.startswith('RS-') and bill[3:].isdigit():
            seq = max(seq, int(bill[3:]))
    bill_number = f'RS-{seq + 1:04d}'
    if any(
        str(row.get('franchise_id')) == str(franchise_id) and row.get('bill_number') == bill_number
        for row in orders
    ):
        raise PosCheckoutError('BILL_NUMBER_CONFLICT')

    now = _now()
    order_id = str(uuid4())
    order_row = {
        'id': order_id,
        'franchise_id': str(franchise_id),
        'bill_number': bill_number,
        'status': 'COMPLETED',
        'customer_phone': phone,
        'subtotal': _as_float(subtotal),
        'discount_amount': _as_float(discount_amount),
        'discount_id': offer_id_str,
        'coupon_id': None,
        'taxable_amount': _as_float(taxable),
        'gst_rate': _as_float(gst_rate),
        'gst_amount': _as_float(gst_amount),
        'cgst_rate': _as_float(cgst_rate),
        'sgst_rate': _as_float(sgst_rate),
        'cgst_amount': _as_float(cgst_amount),
        'sgst_amount': _as_float(sgst_amount),
        'offer_name': offer_name,
        'discount_type': discount_type,
        'discount_value': _as_float(discount_value),
        'total_amount': _as_float(total),
        'payment_method': payment_method,
        'cashier_id': str(cashier_id),
        'completed_at': now,
        'cancelled_at': None,
        'created_at': now,
        'updated_at': now,
    }

    item_rows: list[dict[str, Any]] = []
    for item in built_items:
        item_rows.append(
            {
                'id': str(uuid4()),
                'order_id': order_id,
                'product_id': item['product_id'],
                'product_name_snapshot': item['product_name_snapshot'],
                'unit_price': _as_float(item['unit_price']),
                'quantity': item['quantity'],
                'line_discount_amount': 0,
                'line_total': _as_float(item['line_total']),
                'created_at': now,
            }
        )

    orders.append(order_row)
    tables.setdefault('order_items', []).extend(item_rows)

    payload = deepcopy(order_row)
    payload.update(
        {
            'offer_id': offer_id_str,
            'discount_percent': _as_float(discount_value),
            'cashier_name': cashier.get('full_name'),
            'franchise_name': franchise.get('name'),
            'franchise_address': franchise.get('address'),
            'franchise_city': franchise.get('city'),
            'franchise_state': franchise.get('state'),
            'items': deepcopy(item_rows),
        }
    )
    return payload
