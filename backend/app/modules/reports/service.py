from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import HTTPException, status

from app.core.roles import UserRole
from app.core.security import CurrentProfile
from app.modules.pos.schemas import PosPaymentMethod
from app.modules.reports.dates import (
    ReportPeriod,
    chart_days,
    resolve_report_bounds,
    resolve_sales_date,
    utc_today,
)
from app.modules.reports.pdf import (
    SCOPE_ALL_FRANCHISES,
    TITLE,
    SalesReportExport,
    export_filename,
    format_bill_when,
    format_display_date,
    format_generated_at,
    payment_label,
    period_label,
    render_sales_report_pdf,
)
from app.modules.reports.repository import ReportsRepository
from app.modules.reports.schemas import (
    AdminDashboard,
    AdminOutletPerformance,
    DailyRevenuePoint,
    DailyRevenueResponse,
    EmployeeDailySales,
    EmployeeDailySalesPayments,
    EmployeeDailySalesSummary,
    OwnerDashboard,
    PaymentTotalsResponse,
    PaymentTotalsRow,
    ProductSalesResponse,
    ProductSalesRow,
    ReportBillPreview,
    ReportSummary,
)

TWOPLACES = Decimal('0.01')
PAYMENT_METHODS = (
    PosPaymentMethod.CASH.value,
    PosPaymentMethod.UPI.value,
    PosPaymentMethod.CARD.value,
)
TOP_PRODUCTS_LIMIT = 8
RECENT_BILLS_REPORT = 5
RECENT_BILLS_OWNER = 8


def _money(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _as_float(value: Decimal) -> float:
    return float(value)


def _avg_order(revenue: Decimal, orders: int) -> int:
    if orders <= 0:
        return 0
    return int((revenue / Decimal(orders)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _product_line_revenue(item: dict) -> Decimal:
    unit_price = item.get('unit_price')
    quantity = int(item.get('quantity') or 0)
    if unit_price is not None:
        return _money(unit_price) * quantity
    return _money(item.get('line_total'))


class ReportsService:
    def __init__(self, repo: ReportsRepository | None = None) -> None:
        self.repo = repo or ReportsRepository()

    def summary(
        self,
        profile: CurrentProfile,
        period: ReportPeriod,
        franchise_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ReportSummary:
        scoped = self._report_scope(profile, franchise_id)
        start, end = self._period_window(period, start_date, end_date)
        orders = self.repo.list_completed_orders(
            franchise_id=scoped,
            from_date=start,
            to_date=end,
        )
        items = self.repo.list_order_items([str(row['id']) for row in orders])
        revenue, order_count, items_sold = self._summary_metrics(orders, items)
        recent = [self._to_bill_preview(row) for row in orders[:RECENT_BILLS_REPORT]]
        return ReportSummary(
            revenue=_as_float(revenue),
            orders=order_count,
            avg_order=_avg_order(revenue, order_count),
            items_sold=items_sold,
            recent_bills=recent,
        )

    def daily(
        self,
        profile: CurrentProfile,
        period: ReportPeriod,
        franchise_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> DailyRevenueResponse:
        scoped = self._report_scope(profile, franchise_id)
        start, end = self._period_window(period, start_date, end_date)
        orders = self.repo.list_completed_orders(
            franchise_id=scoped,
            from_date=start,
            to_date=end,
        )
        totals: dict[str, Decimal] = defaultdict(lambda: Decimal('0.00'))
        for row in orders:
            completed = row.get('completed_at')
            if not completed:
                continue
            day_key = str(completed)[:10]
            totals[day_key] += _money(row.get('total_amount'))

        points = [
            DailyRevenuePoint(date=day.isoformat(), revenue=_as_float(totals.get(day.isoformat(), Decimal('0.00'))))
            for day in chart_days(period, start=start, end=end)
        ]
        return DailyRevenueResponse(items=points)

    def products(
        self,
        profile: CurrentProfile,
        period: ReportPeriod,
        franchise_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ProductSalesResponse:
        scoped = self._report_scope(profile, franchise_id)
        start, end = self._period_window(period, start_date, end_date)
        orders = self.repo.list_completed_orders(
            franchise_id=scoped,
            from_date=start,
            to_date=end,
        )
        items = self.repo.list_order_items([str(row['id']) for row in orders])
        return ProductSalesResponse(items=self._top_products(items, limit=TOP_PRODUCTS_LIMIT))

    def payments(
        self,
        profile: CurrentProfile,
        period: ReportPeriod,
        franchise_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> PaymentTotalsResponse:
        scoped = self._report_scope(profile, franchise_id)
        start, end = self._period_window(period, start_date, end_date)
        orders = self.repo.list_completed_orders(
            franchise_id=scoped,
            from_date=start,
            to_date=end,
        )
        totals = {method: Decimal('0.00') for method in PAYMENT_METHODS}
        for row in orders:
            method = row.get('payment_method')
            if method in totals:
                totals[method] += _money(row.get('total_amount'))
        return PaymentTotalsResponse(
            items=[
                PaymentTotalsRow(payment_method=method, amount=_as_float(totals[method]))
                for method in PAYMENT_METHODS
            ]
        )

    def admin_dashboard(self, profile: CurrentProfile) -> AdminDashboard:
        if profile.role != UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions for this resource',
            )

        today = utc_today()
        today_orders = self.repo.list_completed_orders(
            franchise_id=None,
            from_date=today,
            to_date=today,
        )
        all_time_orders = self.repo.list_completed_orders(
            franchise_id=None,
            from_date=None,
            to_date=None,
        )
        today_items = self.repo.list_order_items([str(row['id']) for row in today_orders])
        today_revenue, orders_today, _ = self._summary_metrics(today_orders, today_items)
        all_time_revenue, total_bills, _ = self._summary_metrics(all_time_orders, [])
        top_name, top_qty = self._top_seller(today_items)

        by_franchise: dict[str, list[dict]] = defaultdict(list)
        for row in today_orders:
            by_franchise[str(row['franchise_id'])].append(row)

        outlets: list[AdminOutletPerformance] = []
        for franchise in self.repo.list_franchises():
            franchise_id = str(franchise['id'])
            rows = by_franchise.get(franchise_id, [])
            revenue = sum((_money(row.get('total_amount')) for row in rows), Decimal('0.00'))
            outlets.append(
                AdminOutletPerformance(
                    franchise_id=franchise['id'],
                    franchise_name=franchise.get('name') or 'Outlet',
                    revenue=_as_float(revenue),
                    orders=len(rows),
                )
            )
        outlets.sort(key=lambda row: (-row.revenue, row.franchise_name.lower()))

        return AdminDashboard(
            today_revenue=_as_float(today_revenue),
            orders_today=orders_today,
            active_outlets=self.repo.count_active_outlets(),
            top_seller_name=top_name,
            top_seller_quantity=top_qty,
            outlets=outlets,
            all_time_revenue=_as_float(all_time_revenue),
            total_bills=total_bills,
        )

    def owner_dashboard(self, profile: CurrentProfile) -> OwnerDashboard:
        if profile.role != UserRole.FRANCHISE_OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions for this resource',
            )
        if profile.franchise_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Profile must belong to a franchise',
            )

        today = utc_today()
        franchise_id = profile.franchise_id
        today_orders = self.repo.list_completed_orders(
            franchise_id=franchise_id,
            from_date=today,
            to_date=today,
        )
        all_time_orders = self.repo.list_completed_orders(
            franchise_id=franchise_id,
            from_date=None,
            to_date=None,
        )
        today_items = self.repo.list_order_items([str(row['id']) for row in today_orders])
        today_revenue, bills_today, _ = self._summary_metrics(today_orders, today_items)
        all_time_revenue, _, _ = self._summary_metrics(all_time_orders, [])
        top_name, top_qty = self._top_seller(today_items)
        franchise = self.repo.get_franchise(franchise_id)

        return OwnerDashboard(
            franchise_id=franchise_id,
            franchise_name=(franchise or {}).get('name'),
            today_revenue=_as_float(today_revenue),
            bills_today=bills_today,
            top_product_name=top_name,
            top_product_quantity=top_qty,
            all_time_revenue=_as_float(all_time_revenue),
            recent_bills=[self._to_bill_preview(row) for row in today_orders[:RECENT_BILLS_OWNER]],
        )

    def employee_daily_sales(
        self,
        profile: CurrentProfile,
        franchise_id: UUID | None = None,
        selected_date: date | None = None,
    ) -> EmployeeDailySales:
        del franchise_id  # never trust a client-supplied franchise_id
        if profile.role != UserRole.EMPLOYEE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions for this resource',
            )
        if profile.franchise_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Profile must belong to a franchise',
            )

        try:
            day = resolve_sales_date(selected_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        orders = self.repo.list_completed_orders(
            franchise_id=profile.franchise_id,
            from_date=day,
            to_date=day,
        )
        items = self.repo.list_order_items([str(row['id']) for row in orders])
        revenue, bills, items_sold = self._summary_metrics(orders, items)
        totals = {method: Decimal('0.00') for method in PAYMENT_METHODS}
        for row in orders:
            method = row.get('payment_method')
            if method in totals:
                totals[method] += _money(row.get('total_amount'))

        return EmployeeDailySales(
            date=day.isoformat(),
            summary=EmployeeDailySalesSummary(
                revenue=_as_float(revenue),
                bills=bills,
                items_sold=items_sold,
                average_bill=_avg_order(revenue, bills),
            ),
            payments=EmployeeDailySalesPayments(
                cash=_as_float(totals[PosPaymentMethod.CASH.value]),
                upi=_as_float(totals[PosPaymentMethod.UPI.value]),
                card=_as_float(totals[PosPaymentMethod.CARD.value]),
            ),
            bills=[self._to_bill_preview(row) for row in orders],
        )

    def build_export_payload(
        self,
        profile: CurrentProfile,
        period: ReportPeriod,
        franchise_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        generated_at: datetime | None = None,
    ) -> SalesReportExport:
        summary = self.summary(
            profile,
            period,
            franchise_id,
            start_date=start_date,
            end_date=end_date,
        )
        daily = self.daily(
            profile,
            period,
            franchise_id,
            start_date=start_date,
            end_date=end_date,
        )
        products = self.products(
            profile,
            period,
            franchise_id,
            start_date=start_date,
            end_date=end_date,
        )
        payments = self.payments(
            profile,
            period,
            franchise_id,
            start_date=start_date,
            end_date=end_date,
        )
        start, end = self._period_window(period, start_date, end_date)
        generated = generated_at or datetime.now(timezone.utc)
        return SalesReportExport(
            title=TITLE,
            period_label=period_label(period, start, end),
            scope_label=self._scope_label(profile),
            generated_label=format_generated_at(generated),
            filename=export_filename(period, start, end),
            revenue=summary.revenue,
            orders=summary.orders,
            avg_order=summary.avg_order,
            items_sold=summary.items_sold,
            daily=[
                (format_display_date(date.fromisoformat(point.date)), point.revenue)
                for point in daily.items
            ],
            products=[(row.product_name, row.quantity, row.revenue) for row in products.items],
            payments=[(payment_label(row.payment_method), row.amount) for row in payments.items],
            bills=[
                (
                    bill.bill_number,
                    format_bill_when(bill.completed_at),
                    bill.total_amount,
                    payment_label(bill.payment_method),
                )
                for bill in summary.recent_bills
            ],
            product_details=self._product_detail_rows(
                profile,
                period,
                franchise_id,
                start_date=start_date,
                end_date=end_date,
            ),
        )

    def export_pdf(
        self,
        profile: CurrentProfile,
        period: ReportPeriod,
        franchise_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[bytes, str]:
        report = self.build_export_payload(
            profile,
            period,
            franchise_id,
            start_date=start_date,
            end_date=end_date,
        )
        try:
            return render_sales_report_pdf(report), report.filename
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Unable to generate report.',
            ) from exc

    def _scope_label(self, profile: CurrentProfile) -> str:
        scoped = self._report_scope(profile, None)
        if scoped is None:
            return SCOPE_ALL_FRANCHISES
        franchise = self.repo.get_franchise(scoped)
        name = str((franchise or {}).get('name') or 'Outlet').strip() or 'Outlet'
        return f'Franchise: {name}'

    def _period_window(
        self,
        period: ReportPeriod,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date, date]:
        try:
            return resolve_report_bounds(period, start_date, end_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    def _report_scope(self, profile: CurrentProfile, requested: UUID | None) -> UUID | None:
        del requested  # never trust a client-supplied franchise_id
        if profile.role == UserRole.SYSTEM_ADMIN:
            return None
        if profile.role == UserRole.FRANCHISE_OWNER:
            if profile.franchise_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Profile must belong to a franchise',
                )
            return profile.franchise_id
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Insufficient permissions for this resource',
        )

    def _summary_metrics(
        self,
        orders: list[dict],
        items: list[dict],
    ) -> tuple[Decimal, int, int]:
        revenue = sum((_money(row.get('total_amount')) for row in orders), Decimal('0.00'))
        items_sold = sum(int(item.get('quantity') or 0) for item in items)
        return revenue, len(orders), items_sold

    def _product_detail_rows(
        self,
        profile: CurrentProfile,
        period: ReportPeriod,
        franchise_id: UUID | None,
        start_date: date | None,
        end_date: date | None,
    ) -> list[tuple[str, str, str, float]]:
        scoped = self._report_scope(profile, franchise_id)
        start, end = self._period_window(period, start_date, end_date)
        orders = self.repo.list_completed_orders(
            franchise_id=scoped,
            from_date=start,
            to_date=end,
        )
        items = self.repo.list_order_items([str(row['id']) for row in orders])
        if not items:
            return []

        product_ids = [str(item['product_id']) for item in items if item.get('product_id')]
        products = {str(row['id']): row for row in self.repo.list_products_by_ids(product_ids)}
        category_ids = [
            str(row['category_id']) for row in products.values() if row.get('category_id')
        ]
        categories = {
            str(row['id']): row for row in self.repo.list_categories_by_ids(category_ids)
        }
        order_rank = {str(row['id']): index for index, row in enumerate(orders)}
        order_by_id = {str(row['id']): row for row in orders}

        sorted_items = sorted(
            items,
            key=lambda item: (
                order_rank.get(str(item.get('order_id')), len(order_rank)),
                str(item.get('created_at') or ''),
                str(item.get('id') or ''),
            ),
        )
        rows: list[tuple[str, str, str, float]] = []
        for item in sorted_items:
            order = order_by_id.get(str(item.get('order_id')), {})
            product = products.get(str(item.get('product_id') or ''), {})
            category = categories.get(str(product.get('category_id') or ''), {})
            name = str(item.get('product_name_snapshot') or '').strip() or 'Unknown'
            category_name = str(category.get('name') or '').strip() or '-'
            rows.append(
                (
                    name,
                    category_name,
                    payment_label(order.get('payment_method')),
                    _as_float(_money(item.get('unit_price'))),
                )
            )
        return rows

    def _top_products(self, items: list[dict], *, limit: int) -> list[ProductSalesRow]:
        grouped: dict[str, dict[str, Decimal | int | str]] = {}
        for item in items:
            name = str(item.get('product_name_snapshot') or '').strip() or 'Unknown'
            bucket = grouped.setdefault(name, {'name': name, 'quantity': 0, 'revenue': Decimal('0.00')})
            bucket['quantity'] = int(bucket['quantity']) + int(item.get('quantity') or 0)
            bucket['revenue'] = Decimal(str(bucket['revenue'])) + _product_line_revenue(item)

        ranked = sorted(
            grouped.values(),
            key=lambda row: (-Decimal(str(row['revenue'])), -int(row['quantity']), str(row['name'])),
        )
        return [
            ProductSalesRow(
                product_name=str(row['name']),
                quantity=int(row['quantity']),
                revenue=_as_float(Decimal(str(row['revenue']))),
            )
            for row in ranked[:limit]
        ]

    def _top_seller(self, items: list[dict]) -> tuple[str | None, int]:
        grouped: dict[str, int] = defaultdict(int)
        for item in items:
            name = str(item.get('product_name_snapshot') or '').strip()
            if not name:
                continue
            grouped[name] += int(item.get('quantity') or 0)
        if not grouped:
            return None, 0
        quantity = max(grouped.values())
        tied = sorted(name for name, value in grouped.items() if value == quantity)
        return tied[0], quantity

    def _to_bill_preview(self, row: dict) -> ReportBillPreview:
        return ReportBillPreview(
            id=row['id'],
            bill_number=row['bill_number'],
            completed_at=row.get('completed_at'),
            total_amount=_as_float(_money(row.get('total_amount'))),
            payment_method=row.get('payment_method'),
        )
