from __future__ import annotations

from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError

from app.db.supabase import get_supabase
from app.modules.pos.engine import PosCheckoutError

ORDER_COLUMNS = (
    'id, franchise_id, bill_number, status, customer_phone, subtotal, discount_amount, '
    'discount_id, coupon_id, taxable_amount, gst_rate, gst_amount, cgst_rate, sgst_rate, '
    'cgst_amount, sgst_amount, offer_name, discount_type, discount_value, total_amount, '
    'payment_method, cashier_id, completed_at, cancelled_at, created_at, updated_at'
)

OFFER_COLUMNS = (
    'id, name, description, discount_type, discount_value, is_active, '
    'valid_from, valid_to, franchise_id, promotion_id, created_at, updated_at'
)

ITEM_COLUMNS = (
    'id, order_id, product_id, product_name_snapshot, unit_price, quantity, '
    'line_discount_amount, line_total, created_at'
)


class PosRepository:
    def __init__(self) -> None:
        self._db = get_supabase()

    def list_assignments(self, franchise_id: UUID) -> list[dict[str, Any]]:
        response = (
            self._db.table('franchise_product_prices')
            .select('id, franchise_id, product_id, selling_price, is_active, created_at, updated_at')
            .eq('franchise_id', str(franchise_id))
            .execute()
        )
        return list(response.data or [])

    def get_products_by_ids(self, product_ids: list[str]) -> list[dict[str, Any]]:
        if not product_ids:
            return []
        response = (
            self._db.table('products')
            .select(
                'id, category_id, sku, name, description, image_url, price, is_active, metadata, '
                'created_at, updated_at'
            )
            .in_('id', product_ids)
            .execute()
        )
        return list(response.data or [])

    def list_categories(self) -> list[dict[str, Any]]:
        response = (
            self._db.table('product_categories')
            .select('id, name, display_order, is_active, created_at, updated_at')
            .eq('is_active', True)
            .order('display_order')
            .execute()
        )
        return list(response.data or [])

    def get_franchise(self, franchise_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('franchises')
            .select('id, name, address, city, state, status, is_archived')
            .eq('id', str(franchise_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def list_offers(self) -> list[dict[str, Any]]:
        response = (
            self._db.table('discounts')
            .select(OFFER_COLUMNS)
            .order('name')
            .execute()
        )
        return list(response.data or [])

    def list_promotions(self) -> list[dict[str, Any]]:
        response = (
            self._db.table('promotions')
            .select(
                'id, name, description, promo_code, valid_from, valid_to, is_active, '
                'created_at, updated_at'
            )
            .execute()
        )
        return list(response.data or [])

    def list_promotion_franchise_map(self, promotion_ids: list[str]) -> dict[str, list[str]]:
        unique_ids = [pid for pid in dict.fromkeys(promotion_ids) if pid]
        if not unique_ids:
            return {}
        response = (
            self._db.table('promotion_franchises')
            .select('promotion_id, franchise_id')
            .in_('promotion_id', unique_ids)
            .execute()
        )
        mapping: dict[str, list[str]] = {pid: [] for pid in unique_ids}
        for row in response.data or []:
            mapping.setdefault(str(row['promotion_id']), []).append(str(row['franchise_id']))
        return mapping

    def get_active_gst(self) -> dict[str, Any] | None:
        response = (
            self._db.table('gst_settings')
            .select('id, rate, is_active, created_at, updated_at')
            .eq('is_active', True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def get_order(self, order_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('orders')
            .select(ORDER_COLUMNS)
            .eq('id', str(order_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def list_order_items(self, order_id: UUID) -> list[dict[str, Any]]:
        response = (
            self._db.table('order_items')
            .select(ITEM_COLUMNS)
            .eq('order_id', str(order_id))
            .execute()
        )
        return list(response.data or [])

    def get_profile(self, profile_id: UUID) -> dict[str, Any] | None:
        response = (
            self._db.table('profiles')
            .select('id, full_name, role, franchise_id, is_active')
            .eq('id', str(profile_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def complete_order(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._db.rpc('complete_pos_order', params).execute()
        except PosCheckoutError:
            raise
        except APIError as exc:
            raise PosCheckoutError(_error_code_from_exc(exc), str(exc)) from exc
        except Exception as exc:
            if isinstance(exc, PosCheckoutError):
                raise
            text = str(exc)
            if 'POS_ERROR:' in text:
                raise PosCheckoutError(_error_code_from_exc(exc), text) from exc
            # In-memory FakeDatabase implements rpc(); live Supabase uses the SQL function.
            if hasattr(self._db, 'tables'):
                raise
            raise PosCheckoutError('CHECKOUT_FAILED', text) from exc

        data = response.data
        if isinstance(data, list):
            if not data:
                raise PosCheckoutError('CHECKOUT_FAILED', 'Checkout returned no data')
            data = data[0]
        if not isinstance(data, dict):
            raise PosCheckoutError('CHECKOUT_FAILED', 'Checkout returned no data')
        return data


def _error_code_from_exc(exc: Exception) -> str:
    text = str(exc)
    details = getattr(exc, 'message', None) or getattr(exc, 'details', None) or ''
    blob = f'{text} {details}'
    marker = 'POS_ERROR:'
    if marker in blob:
        code = blob.split(marker, 1)[1]
        return code.split()[0].split(':')[0].strip('.,;')
    return 'CHECKOUT_FAILED'
