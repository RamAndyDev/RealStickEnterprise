from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.roles import UserRole
from app.core.security import CurrentProfile, require_role
from app.modules.reports.dates import ReportPeriod
from app.modules.reports.schemas import (
    AdminDashboard,
    DailyRevenueResponse,
    EmployeeDailySales,
    OwnerDashboard,
    PaymentTotalsResponse,
    ProductSalesResponse,
    ReportSummary,
)
from app.modules.reports.service import ReportsService

router = APIRouter(prefix='/reports', tags=['reports'])

ReportsUser = Annotated[
    CurrentProfile,
    Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.FRANCHISE_OWNER)),
]
SystemAdmin = Annotated[CurrentProfile, Depends(require_role(UserRole.SYSTEM_ADMIN))]
FranchiseOwner = Annotated[CurrentProfile, Depends(require_role(UserRole.FRANCHISE_OWNER))]
EmployeeUser = Annotated[CurrentProfile, Depends(require_role(UserRole.EMPLOYEE))]


def get_reports_service() -> ReportsService:
    return ReportsService()


@router.get('/summary', response_model=ReportSummary)
def get_report_summary(
    profile: ReportsUser,
    period: ReportPeriod = Query(default=ReportPeriod.LAST_7_DAYS),
    franchise_id: UUID | None = Query(default=None),
    service: ReportsService = Depends(get_reports_service),
) -> ReportSummary:
    return service.summary(profile, period, franchise_id)


@router.get('/daily', response_model=DailyRevenueResponse)
def get_daily_revenue(
    profile: ReportsUser,
    period: ReportPeriod = Query(default=ReportPeriod.LAST_7_DAYS),
    franchise_id: UUID | None = Query(default=None),
    service: ReportsService = Depends(get_reports_service),
) -> DailyRevenueResponse:
    return service.daily(profile, period, franchise_id)


@router.get('/products', response_model=ProductSalesResponse)
def get_product_sales(
    profile: ReportsUser,
    period: ReportPeriod = Query(default=ReportPeriod.LAST_7_DAYS),
    franchise_id: UUID | None = Query(default=None),
    service: ReportsService = Depends(get_reports_service),
) -> ProductSalesResponse:
    return service.products(profile, period, franchise_id)


@router.get('/payments', response_model=PaymentTotalsResponse)
def get_payment_totals(
    profile: ReportsUser,
    period: ReportPeriod = Query(default=ReportPeriod.LAST_7_DAYS),
    franchise_id: UUID | None = Query(default=None),
    service: ReportsService = Depends(get_reports_service),
) -> PaymentTotalsResponse:
    return service.payments(profile, period, franchise_id)


@router.get('/dashboard/admin', response_model=AdminDashboard)
def get_admin_dashboard(
    profile: SystemAdmin,
    service: ReportsService = Depends(get_reports_service),
) -> AdminDashboard:
    return service.admin_dashboard(profile)


@router.get('/dashboard/owner', response_model=OwnerDashboard)
def get_owner_dashboard(
    profile: FranchiseOwner,
    service: ReportsService = Depends(get_reports_service),
) -> OwnerDashboard:
    return service.owner_dashboard(profile)


@router.get('/employee/daily', response_model=EmployeeDailySales)
def get_employee_daily_sales(
    profile: EmployeeUser,
    date: date | None = Query(default=None),
    franchise_id: UUID | None = Query(default=None),
    service: ReportsService = Depends(get_reports_service),
) -> EmployeeDailySales:
    return service.employee_daily_sales(profile, franchise_id, date)
