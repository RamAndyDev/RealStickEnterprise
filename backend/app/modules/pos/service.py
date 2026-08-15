from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status

from app.core.gst import split_gst_rate
from app.core.roles import UserRole
from app.core.security import CurrentProfile
from app.modules.pos.engine import PosCheckoutError
from app.modules.pos.repository import PosRepository
from app.modules.pos.schemas import (
    PosMenuCategory,
    PosMenuItem,
    PosMenuResponse,
    PosOffer,
    PosOfferListResponse,
    PosOrder,
    PosOrderCreate,
    PosOrderItem,
    PosPaymentMethod,
)

_POS_ERROR_HTTP: dict[str, tuple[int, str]] = {
    'FRANCHISE_NOT_FOUND': (status.HTTP_404_NOT_FOUND, 'Franchise not found'),
    'CASHIER_INVALID': (status.HTTP_403_FORBIDDEN, 'Cashier profile is not valid for POS'),
    'FRANCHISE_MISMATCH': (status.HTTP_403_FORBIDDEN, 'Access to this franchise is not allowed'),
    'ROLE_NOT_ALLOWED': (status.HTTP_403_FORBIDDEN, 'Insufficient permissions for this resource'),
    'INVALID_PAYMENT': (status.HTTP_422_UNPROCESSABLE_ENTITY, 'Payment method is not supported'),
    'INVALID_DISCOUNT': (status.HTTP_422_UNPROCESSABLE_ENTITY, 'Discount must be between 0 and 100'),
    'DISCOUNT_NOT_ALLOWED': (status.HTTP_403_FORBIDDEN, 'Employees cannot invent a discount'),
    'EMPTY_CART': (status.HTTP_422_UNPROCESSABLE_ENTITY, 'Cart must contain at least one item'),
    'CART_TOO_LARGE': (status.HTTP_422_UNPROCESSABLE_ENTITY, 'Cart has too many items'),
    'INVALID_ITEM': (status.HTTP_422_UNPROCESSABLE_ENTITY, 'Cart item is invalid'),
    'INVALID_QUANTITY': (status.HTTP_422_UNPROCESSABLE_ENTITY, 'Quantity must be an integer between 1 and 999'),
    'GST_UNAVAILABLE': (status.HTTP_503_SERVICE_UNAVAILABLE, 'GST is not configured'),
    'UNASSIGNED_PRODUCT': (status.HTTP_400_BAD_REQUEST, 'Product is not assigned to this franchise'),
    'INACTIVE_PRODUCT': (status.HTTP_400_BAD_REQUEST, 'Product is not available for POS'),
    'INACTIVE_CATEGORY': (status.HTTP_400_BAD_REQUEST, 'Product is not available for POS'),
    'INACTIVE_ASSIGNMENT': (status.HTTP_400_BAD_REQUEST, 'Product is not available for this franchise'),
    'BILL_NUMBER_CONFLICT': (status.HTTP_409_CONFLICT, 'Unable to allocate a bill number'),
    'CHECKOUT_FAILED': (status.HTTP_503_SERVICE_UNAVAILABLE, 'Unable to complete order'),
    'OFFER_INVALID': (status.HTTP_422_UNPROCESSABLE_ENTITY, 'Offer is not valid'),
    'OFFER_INACTIVE': (status.HTTP_422_UNPROCESSABLE_ENTITY, 'Offer is not active'),
    'OFFER_EXPIRED': (status.HTTP_422_UNPROCESSABLE_ENTITY, 'Offer is not currently valid'),
    'OFFER_NOT_YET_VALID': (status.HTTP_422_UNPROCESSABLE_ENTITY, 'Offer is not currently valid'),
    'OFFER_NOT_APPLICABLE': (status.HTTP_403_FORBIDDEN, 'Offer is not applicable to this franchise'),
}


def _money(value: object) -> float:
    return float(Decimal(str(value)))


def _resolve_image_url(row: dict) -> str | None:
    meta = row.get('metadata') or {}
    if isinstance(meta, dict):
        url = meta.get('image_url')
        if isinstance(url, str) and url.strip():
            return url.strip()
    column = row.get('image_url')
    if isinstance(column, str) and column.strip():
        return column.strip()
    return None


def _raise_pos_error(exc: PosCheckoutError) -> None:
    status_code, detail = _POS_ERROR_HTTP.get(
        exc.code,
        (status.HTTP_503_SERVICE_UNAVAILABLE, 'Unable to complete order'),
    )
    raise HTTPException(status_code=status_code, detail=detail) from exc


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


def offer_is_applicable(row: dict, *, franchise_id: UUID, now: datetime) -> bool:
    if not row.get('is_active'):
        return False
    if str(row.get('discount_type') or 'PERCENTAGE') != 'PERCENTAGE':
        return False
    offer_franchise = row.get('franchise_id')
    if offer_franchise not in (None, '') and str(offer_franchise) != str(franchise_id):
        return False
    valid_from = _parse_dt(row.get('valid_from'))
    valid_to = _parse_dt(row.get('valid_to'))
    if valid_from and valid_from > now:
        return False
    if valid_to and valid_to < now:
        return False
    return True


class PosService:
    def __init__(self, repo: PosRepository | None = None) -> None:
        self.repo = repo or PosRepository()

    def _require_pos_franchise(self, profile: CurrentProfile) -> UUID:
        if profile.role != UserRole.EMPLOYEE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions for this resource',
            )
        if profile.franchise_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='POS profile must belong to a franchise',
            )
        return profile.franchise_id

    def get_menu(self, profile: CurrentProfile) -> PosMenuResponse:
        franchise_id = self._require_pos_franchise(profile)
        franchise = self.repo.get_franchise(franchise_id)
        if not franchise:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        gst = self.repo.get_active_gst()
        gst_rate = None
        cgst_rate = None
        sgst_rate = None
        if gst and gst.get('rate') is not None:
            try:
                gst_rate = _money(gst['rate'])
                half_cgst, half_sgst = split_gst_rate(gst['rate'])
                cgst_rate = float(half_cgst)
                sgst_rate = float(half_sgst)
            except ValueError:
                gst_rate = None

        assignments = self.repo.list_assignments(franchise_id)
        product_ids = [str(row['product_id']) for row in assignments]
        products = {str(row['id']): row for row in self.repo.get_products_by_ids(product_ids)}
        categories = {
            str(row['id']): row
            for row in self.repo.list_categories()
        }

        items: list[PosMenuItem] = []
        used_category_ids: set[str] = set()
        for assignment in assignments:
            product = products.get(str(assignment['product_id']))
            if not product:
                continue
            category_id = product.get('category_id')
            category = categories.get(str(category_id)) if category_id else None
            if category_id and not category:
                continue
            product_active = bool(product.get('is_active', True))
            assignment_active = bool(assignment.get('is_active', True))
            category_active = True
            if category_id:
                category_active = bool(category and category.get('is_active', True))
            available = product_active and assignment_active and category_active
            if not available:
                continue
            if category_id:
                used_category_ids.add(str(category_id))
            items.append(
                PosMenuItem(
                    product_id=product['id'],
                    name=product['name'],
                    description=product.get('description'),
                    image_url=_resolve_image_url(product),
                    category_id=category_id,
                    category_name=category.get('name') if category else None,
                    selling_price=_money(assignment['selling_price']),
                    available_for_pos=available,
                )
            )

        items.sort(key=lambda item: ((item.category_name or ''), item.name))
        category_models = [
            PosMenuCategory(
                id=row['id'],
                name=row['name'],
                display_order=row.get('display_order') or 0,
            )
            for row in sorted(
                (categories[cid] for cid in used_category_ids if cid in categories),
                key=lambda row: (row.get('display_order') or 0, row.get('name') or ''),
            )
        ]

        return PosMenuResponse(
            franchise_id=franchise_id,
            franchise_name=franchise.get('name'),
            gst_rate=gst_rate,
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            categories=category_models,
            items=items,
        )

    def list_offers(self, profile: CurrentProfile) -> PosOfferListResponse:
        franchise_id = self._require_pos_franchise(profile)
        now = datetime.now(timezone.utc)
        items: list[PosOffer] = []
        for row in self.repo.list_offers():
            if not offer_is_applicable(row, franchise_id=franchise_id, now=now):
                continue
            items.append(
                PosOffer(
                    id=row['id'],
                    name=row['name'],
                    description=row.get('description'),
                    discount_type=str(row.get('discount_type') or 'PERCENTAGE'),
                    discount_value=_money(row['discount_value']),
                    valid_from=_parse_dt(row.get('valid_from')),
                    valid_to=_parse_dt(row.get('valid_to')),
                )
            )
        items.sort(key=lambda item: item.name.lower())
        return PosOfferListResponse(items=items, total=len(items))

    def complete_order(self, profile: CurrentProfile, body: PosOrderCreate) -> PosOrder:
        franchise_id = self._require_pos_franchise(profile)
        if body.payment_method not in {
            PosPaymentMethod.CASH,
            PosPaymentMethod.UPI,
            PosPaymentMethod.CARD,
        }:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='Payment method is not supported',
            )

        params = {
            'p_franchise_id': str(franchise_id),
            'p_cashier_id': str(profile.id),
            'p_cashier_role': profile.role.value,
            'p_payment_method': body.payment_method.value,
            'p_customer_phone': body.customer_phone,
            'p_offer_id': str(body.offer_id) if body.offer_id else None,
            'p_items': [
                {'product_id': str(item.product_id), 'quantity': item.quantity}
                for item in body.items
            ],
        }
        try:
            payload = self.repo.complete_order(params)
        except PosCheckoutError as exc:
            _raise_pos_error(exc)
        return self._to_order(payload, include_items=True)

    def get_order(self, profile: CurrentProfile, order_id: UUID) -> PosOrder:
        franchise_id = self._require_pos_franchise(profile)
        row = self.repo.get_order(order_id)
        if not row or str(row.get('franchise_id')) != str(franchise_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
        if row.get('status') != 'COMPLETED':
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')

        items = self.repo.list_order_items(order_id)
        franchise = self.repo.get_franchise(franchise_id)
        cashier_name = None
        if row.get('cashier_id'):
            cashier = self.repo.get_profile(UUID(str(row['cashier_id'])))
            if cashier:
                cashier_name = cashier.get('full_name')

        payload = dict(row)
        payload['items'] = items
        payload['cashier_name'] = cashier_name
        if franchise:
            payload.setdefault('franchise_name', franchise.get('name'))
            payload.setdefault('franchise_address', franchise.get('address'))
            payload.setdefault('franchise_city', franchise.get('city'))
            payload.setdefault('franchise_state', franchise.get('state'))
        return self._to_order(payload, include_items=True)

    def _to_order(self, row: dict, *, include_items: bool) -> PosOrder:
        raw_items = row.get('items') or []
        items = [
            PosOrderItem(
                id=item.get('id'),
                product_id=item['product_id'],
                product_name_snapshot=item['product_name_snapshot'],
                unit_price=_money(item['unit_price']),
                quantity=int(item['quantity']),
                line_discount_amount=_money(item.get('line_discount_amount') or 0),
                line_total=_money(item['line_total']),
            )
            for item in raw_items
        ] if include_items else []

        status_value = row.get('status') or 'COMPLETED'
        payment_status = 'PAID' if status_value == 'COMPLETED' and row.get('payment_method') else None

        discount_value = row.get('discount_value')
        if discount_value is None:
            discount_value = row.get('discount_percent')
        offer_id = row.get('offer_id') or row.get('discount_id')

        return PosOrder(
            id=row['id'],
            franchise_id=row['franchise_id'],
            bill_number=row['bill_number'],
            status=status_value,
            customer_phone=row.get('customer_phone'),
            subtotal=_money(row.get('subtotal') or 0),
            discount_amount=_money(row.get('discount_amount') or 0),
            discount_percent=_money(discount_value) if discount_value is not None else None,
            discount_value=_money(discount_value) if discount_value is not None else None,
            discount_type=row.get('discount_type'),
            offer_id=offer_id,
            offer_name=row.get('offer_name'),
            taxable_amount=_money(row.get('taxable_amount') or 0),
            gst_rate=_money(row.get('gst_rate') or 0),
            gst_amount=_money(row.get('gst_amount') or 0),
            cgst_rate=_money(row.get('cgst_rate') or 0),
            sgst_rate=_money(row.get('sgst_rate') or 0),
            cgst_amount=_money(row.get('cgst_amount') or 0),
            sgst_amount=_money(row.get('sgst_amount') or 0),
            total_amount=_money(row.get('total_amount') or 0),
            payment_method=row.get('payment_method'),
            cashier_id=row.get('cashier_id'),
            cashier_name=row.get('cashier_name'),
            completed_at=row.get('completed_at'),
            cancelled_at=row.get('cancelled_at'),
            created_at=row['created_at'],
            updated_at=row.get('updated_at'),
            franchise_name=row.get('franchise_name'),
            franchise_address=row.get('franchise_address'),
            franchise_city=row.get('franchise_city'),
            franchise_state=row.get('franchise_state'),
            items=items,
            payment_status=payment_status,
        )
