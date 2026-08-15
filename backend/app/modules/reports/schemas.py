from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.reports.dates import ReportPeriod

__all__ = [
    'ReportPeriod',
    'ReportSummary',
    'DailyRevenuePoint',
    'DailyRevenueResponse',
    'ProductSalesRow',
    'ProductSalesResponse',
    'PaymentTotalsRow',
    'PaymentTotalsResponse',
    'ReportBillPreview',
    'AdminOutletPerformance',
    'AdminDashboard',
    'OwnerDashboard',
    'EmployeeDailySalesSummary',
    'EmployeeDailySalesPayments',
    'EmployeeDailySales',
]


class ReportBillPreview(BaseModel):
    id: UUID
    bill_number: str
    completed_at: datetime | None = None
    total_amount: float
    payment_method: str | None = None


class ReportSummary(BaseModel):
    revenue: float
    orders: int = Field(ge=0)
    avg_order: int = Field(ge=0)
    items_sold: int = Field(ge=0)
    recent_bills: list[ReportBillPreview] = Field(default_factory=list)


class DailyRevenuePoint(BaseModel):
    date: str
    revenue: float


class DailyRevenueResponse(BaseModel):
    items: list[DailyRevenuePoint]


class ProductSalesRow(BaseModel):
    product_name: str
    quantity: int = Field(ge=0)
    revenue: float


class ProductSalesResponse(BaseModel):
    items: list[ProductSalesRow]


class PaymentTotalsRow(BaseModel):
    payment_method: str
    amount: float


class PaymentTotalsResponse(BaseModel):
    items: list[PaymentTotalsRow]


class AdminOutletPerformance(BaseModel):
    franchise_id: UUID
    franchise_name: str
    revenue: float
    orders: int = Field(ge=0)


class AdminDashboard(BaseModel):
    today_revenue: float
    orders_today: int = Field(ge=0)
    active_outlets: int = Field(ge=0)
    top_seller_name: str | None = None
    top_seller_quantity: int = Field(ge=0)
    outlets: list[AdminOutletPerformance]
    all_time_revenue: float
    total_bills: int = Field(ge=0)


class OwnerDashboard(BaseModel):
    franchise_id: UUID
    franchise_name: str | None = None
    today_revenue: float
    bills_today: int = Field(ge=0)
    top_product_name: str | None = None
    top_product_quantity: int = Field(ge=0)
    all_time_revenue: float
    recent_bills: list[ReportBillPreview]


class EmployeeDailySalesSummary(BaseModel):
    revenue: float
    bills: int = Field(ge=0)
    items_sold: int = Field(ge=0)
    average_bill: int = Field(ge=0)


class EmployeeDailySalesPayments(BaseModel):
    cash: float
    upi: float
    card: float


class EmployeeDailySales(BaseModel):
    date: str
    summary: EmployeeDailySalesSummary
    payments: EmployeeDailySalesPayments
    bills: list[ReportBillPreview] = Field(default_factory=list)
