from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status

from app.core.roles import UserRole
from app.core.security import CurrentProfile
from app.modules.orders.repository import OrdersRepository
from app.modules.orders.schemas import BillListItem, BillListResponse
from app.modules.pos.schemas import PosOrder, PosOrderItem, PosPaymentMethod


def _money(value: object) -> float:
    return float(Decimal(str(value)))


class OrdersService:
    def __init__(self, repo: OrdersRepository | None = None) -> None:
        self.repo = repo or OrdersRepository()

    def list_bills(
        self,
        profile: CurrentProfile,
        *,
        franchise_id: UUID | None,
        bill_number: str | None,
        payment_method: PosPaymentMethod | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> BillListResponse:
        scoped_franchise_id = self._list_franchise_scope(profile, franchise_id)
        if from_date is not None and to_date is not None and from_date > to_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='from_date must be on or before to_date',
            )

        needle = (bill_number or '').strip() or None
        rows, total = self.repo.list_completed_orders(
            franchise_id=scoped_franchise_id,
            bill_number=needle,
            payment_method=payment_method.value if payment_method else None,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )

        cashier_ids = list({str(row['cashier_id']) for row in rows if row.get('cashier_id')})
        franchise_ids = list({str(row['franchise_id']) for row in rows if row.get('franchise_id')})
        cashiers = {
            str(row['id']): row.get('full_name')
            for row in self.repo.list_profiles_by_ids(cashier_ids)
        }
        franchises = {
            str(row['id']): row.get('name')
            for row in self.repo.list_franchises_by_ids(franchise_ids)
        }

        items = [
            BillListItem(
                id=row['id'],
                bill_number=row['bill_number'],
                franchise_id=row['franchise_id'],
                franchise_name=franchises.get(str(row['franchise_id'])),
                cashier_id=row.get('cashier_id'),
                cashier_name=cashiers.get(str(row['cashier_id'])) if row.get('cashier_id') else None,
                created_at=row['created_at'],
                completed_at=row.get('completed_at'),
                total_amount=_money(row.get('total_amount') or 0),
                payment_method=row.get('payment_method'),
            )
            for row in rows
        ]
        return BillListResponse(items=items, page=page, page_size=page_size, total=total)

    def get_bill(self, profile: CurrentProfile, order_id: UUID) -> PosOrder:
        row = self.repo.get_order(order_id)
        if not row or row.get('status') != 'COMPLETED':
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')

        order_franchise = UUID(str(row['franchise_id']))
        self._assert_can_read_franchise(profile, order_franchise)

        items = self.repo.list_order_items(order_id)
        franchise = self.repo.get_franchise(order_franchise)
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
        return self._to_order(payload)

    def _list_franchise_scope(
        self,
        profile: CurrentProfile,
        requested: UUID | None,
    ) -> UUID | None:
        if profile.role in {UserRole.EMPLOYEE, UserRole.FRANCHISE_OWNER}:
            if profile.franchise_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Profile must belong to a franchise',
                )
            return profile.franchise_id

        if profile.role != UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions for this resource',
            )
        return requested

    def _assert_can_read_franchise(self, profile: CurrentProfile, franchise_id: UUID) -> None:
        if profile.role == UserRole.SYSTEM_ADMIN:
            return
        if profile.franchise_id is None or profile.franchise_id != franchise_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')

    def _to_order(self, row: dict) -> PosOrder:
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
            for item in (row.get('items') or [])
        ]

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
