"""Observation #14 — sales report PDF export."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.core.roles import UserRole
from app.core.security import CurrentProfile
from app.modules.reports.dates import ReportPeriod
from app.modules.reports.pdf import (
    BRAND_NAME,
    EMPTY_PRODUCT_SALES,
    SCOPE_ALL_FRANCHISES,
    TITLE,
    SalesReportExport,
    brand_logo_path,
    export_filename,
    format_inr,
    period_label,
    render_sales_report_pdf,
)
from app.modules.reports.service import ReportsService
from tests.conftest import (
    ADMIN_ID,
    FRANCHISE_A,
    FRANCHISE_B,
    OWNER_ID,
    PRODUCT_NIMBU,
    PRODUCT_ORANGE,
)
from tests.test_reports import (
    _admin,
    _assign_nimbu_b,
    _assign_orange_a,
    _checkout,
    _custom_params,
    _employee,
    _employee_b,
    _owner,
    _seed_order,
)

EXPORT = '/api/v1/reports/export'


def _owner_profile() -> CurrentProfile:
    return CurrentProfile(
        id=OWNER_ID,
        email='owner@realstick.in',
        full_name='Franchise Owner',
        role=UserRole.FRANCHISE_OWNER,
        franchise_id=FRANCHISE_A,
        is_active=True,
    )


def _admin_profile() -> CurrentProfile:
    return CurrentProfile(
        id=ADMIN_ID,
        email='admin@realstick.in',
        full_name='System Admin',
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
    )


def _pdf_headers(response) -> str:
    return response.headers.get('content-disposition', '')


def test_unauthenticated_export_is_rejected(client):
    assert client.get(EXPORT).status_code == 401


def test_employee_cannot_export_reports(client, auth_header_factory):
    response = client.get(EXPORT, headers=_employee(auth_header_factory), params={'period': 'today'})
    assert response.status_code == 403
    assert response.json()['detail'] == 'Insufficient permissions for this resource'


def test_admin_can_generate_today_report(client, auth_header_factory):
    created = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert created.status_code == 201
    response = client.get(EXPORT, headers=_admin(auth_header_factory), params={'period': 'today'})
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/pdf')
    assert response.content.startswith(b'%PDF')
    assert b'Sales Report' in response.content
    assert BRAND_NAME.encode() in response.content
    assert b'Product Sales Details' in response.content
    assert b'Today' in response.content
    assert SCOPE_ALL_FRANCHISES.encode() in response.content
    assert 'attachment' in _pdf_headers(response)
    assert 'sales-report-today.pdf' in _pdf_headers(response)
    assert str(FRANCHISE_A).encode() not in response.content
    assert created.json()['id'].encode() not in response.content
    assert created.json()['bill_number'].encode() in response.content


def test_owner_can_generate_report_for_own_franchise(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory), payment_method='UPI')
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='CARD')
    assert other.status_code == 201

    response = client.get(EXPORT, headers=_owner(auth_header_factory), params={'period': 'today'})
    assert response.status_code == 200
    assert response.content.startswith(b'%PDF')
    assert b'Franchise: Hyderabad' in response.content
    assert SCOPE_ALL_FRANCHISES.encode() not in response.content
    assert 'sales-report-today.pdf' in _pdf_headers(response)
    assert str(FRANCHISE_B).encode() not in response.content

    owner_payload = ReportsService().build_export_payload(_owner_profile(), ReportPeriod.TODAY)
    admin_payload = ReportsService().build_export_payload(_admin_profile(), ReportPeriod.TODAY)
    assert owner_payload.orders == 1
    assert owner_payload.revenue == own.json()['total_amount']
    assert admin_payload.orders == 2
    assert admin_payload.revenue == own.json()['total_amount'] + other.json()['total_amount']


def test_owner_supplied_franchise_id_cannot_widen_export_scope(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='UPI')
    assert other.status_code == 201

    response = client.get(
        EXPORT,
        headers=_owner(auth_header_factory),
        params={'period': 'today', 'franchise_id': str(FRANCHISE_B)},
    )
    assert response.status_code == 200
    payload = ReportsService().build_export_payload(
        _owner_profile(),
        ReportPeriod.TODAY,
        franchise_id=FRANCHISE_B,
    )
    summary = client.get(
        '/api/v1/reports/summary',
        headers=_owner(auth_header_factory),
        params={'period': 'today', 'franchise_id': str(FRANCHISE_B)},
    ).json()
    assert payload.orders == 1
    assert payload.revenue == own.json()['total_amount']
    assert payload.revenue == summary['revenue']
    assert payload.orders == summary['orders']
    assert payload.revenue != own.json()['total_amount'] + other.json()['total_amount']


def test_last_7_days_export_filename(client, auth_header_factory):
    response = client.get(EXPORT, headers=_owner(auth_header_factory), params={'period': '7d'})
    assert response.status_code == 200
    assert response.content.startswith(b'%PDF')
    assert b'Last 7 Days' in response.content
    assert 'sales-report-last-7-days.pdf' in _pdf_headers(response)


def test_last_30_days_export_filename(client, auth_header_factory):
    response = client.get(EXPORT, headers=_admin(auth_header_factory), params={'period': '30d'})
    assert response.status_code == 200
    assert response.content.startswith(b'%PDF')
    assert b'Last 30 Days' in response.content
    assert 'sales-report-last-30-days.pdf' in _pdf_headers(response)


def test_custom_date_range_export(client, auth_header_factory, fake_db):
    in_range = _seed_order(
        fake_db,
        status='COMPLETED',
        franchise_id=FRANCHISE_A,
        total_amount=50,
        payment_method='CASH',
        completed_at=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc).isoformat(),
        bill_number='RS-INRANGE',
    )
    _seed_order(
        fake_db,
        status='COMPLETED',
        franchise_id=FRANCHISE_A,
        total_amount=999,
        payment_method='UPI',
        completed_at=datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc).isoformat(),
        bill_number='RS-OUTSIDE',
    )
    response = client.get(
        EXPORT,
        headers=_owner(auth_header_factory),
        params=_custom_params('2026-08-01', '2026-08-10'),
    )
    assert response.status_code == 200
    assert b'01 Aug 2026 - 10 Aug 2026' in response.content
    assert b'RS-INRANGE' in response.content
    assert b'RS-OUTSIDE' not in response.content
    assert 'sales-report-2026-08-01-to-2026-08-10.pdf' in _pdf_headers(response)
    assert in_range


def test_custom_range_export_includes_end_date(client, auth_header_factory, fake_db):
    late = _seed_order(
        fake_db,
        status='COMPLETED',
        franchise_id=FRANCHISE_A,
        total_amount=25,
        payment_method='UPI',
        completed_at=datetime(2026, 8, 10, 23, 59, 59, tzinfo=timezone.utc).isoformat(),
        bill_number='RS-ENDDAY',
    )
    _seed_order(
        fake_db,
        status='COMPLETED',
        franchise_id=FRANCHISE_A,
        total_amount=70,
        payment_method='CARD',
        completed_at=datetime(2026, 8, 11, 0, 0, tzinfo=timezone.utc).isoformat(),
        bill_number='RS-NEXTDAY',
    )
    response = client.get(
        EXPORT,
        headers=_owner(auth_header_factory),
        params=_custom_params('2026-08-01', '2026-08-10'),
    )
    summary = client.get(
        '/api/v1/reports/summary',
        headers=_owner(auth_header_factory),
        params=_custom_params('2026-08-01', '2026-08-10'),
    ).json()
    assert response.status_code == 200
    assert b'RS-ENDDAY' in response.content
    assert b'RS-NEXTDAY' not in response.content
    assert summary['orders'] == 1
    assert summary['revenue'] == 25
    assert late


def test_custom_range_export_rejects_start_after_end(client, auth_header_factory):
    response = client.get(
        EXPORT,
        headers=_owner(auth_header_factory),
        params=_custom_params('2026-08-10', '2026-08-01'),
    )
    assert response.status_code == 422
    assert response.json()['detail'] == 'Start date cannot be after end date.'


def test_custom_range_export_requires_start_and_end_dates(client, auth_header_factory):
    missing_start = client.get(
        EXPORT,
        headers=_owner(auth_header_factory),
        params={'period': 'custom', 'end_date': '2026-08-10'},
    )
    missing_end = client.get(
        EXPORT,
        headers=_owner(auth_header_factory),
        params={'period': 'custom', 'start_date': '2026-08-01'},
    )
    assert missing_start.status_code == 422
    assert missing_start.json()['detail'] == 'Start date is required.'
    assert missing_end.status_code == 422
    assert missing_end.json()['detail'] == 'End date is required.'


def test_export_reuses_existing_report_calculations(client, auth_header_factory):
    first = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    second = _checkout(
        client,
        _employee(auth_header_factory),
        items=[{'product_id': str(PRODUCT_NIMBU), 'quantity': 3}],
        payment_method='CARD',
    )
    assert first.status_code == 201
    assert second.status_code == 201

    params = {'period': 'today'}
    headers = _owner(auth_header_factory)
    summary = client.get('/api/v1/reports/summary', headers=headers, params=params).json()
    daily = client.get('/api/v1/reports/daily', headers=headers, params=params).json()
    products = client.get('/api/v1/reports/products', headers=headers, params=params).json()
    payments = client.get('/api/v1/reports/payments', headers=headers, params=params).json()
    payload = ReportsService().build_export_payload(_owner_profile(), ReportPeriod.TODAY)

    assert payload.title == TITLE
    assert payload.revenue == summary['revenue']
    assert payload.orders == summary['orders']
    assert payload.avg_order == summary['avg_order']
    assert payload.items_sold == summary['items_sold']
    assert [row[1] for row in payload.daily] == [point['revenue'] for point in daily['items']]
    assert [row[0] for row in payload.products] == [row['product_name'] for row in products['items']]
    assert [row[1] for row in payload.payments] == [row['amount'] for row in payments['items']]
    assert [row[0] for row in payload.bills] == [bill['bill_number'] for bill in summary['recent_bills']]


def test_admin_export_is_all_franchises(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory))
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory)
    other = _checkout(client, _employee_b(auth_header_factory))
    assert other.status_code == 201

    summary = client.get(
        '/api/v1/reports/summary',
        headers=_admin(auth_header_factory),
        params={'period': 'today'},
    ).json()
    payload = ReportsService().build_export_payload(
        _admin_profile(),
        ReportPeriod.TODAY,
        franchise_id=FRANCHISE_A,
    )
    assert payload.scope_label == SCOPE_ALL_FRANCHISES
    assert payload.orders == 2
    assert payload.orders == summary['orders']
    assert payload.revenue == summary['revenue']


def test_period_filters_apply_to_export(client, auth_header_factory, fake_db):
    created = _checkout(client, _employee(auth_header_factory))
    assert created.status_code == 201
    order_id = created.json()['id']
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    row = next(item for item in fake_db.tables['orders'] if item['id'] == order_id)
    row['completed_at'] = old
    row['created_at'] = old

    today = ReportsService().build_export_payload(_owner_profile(), ReportPeriod.TODAY)
    week = ReportsService().build_export_payload(_owner_profile(), ReportPeriod.LAST_7_DAYS)
    month = ReportsService().build_export_payload(_owner_profile(), ReportPeriod.LAST_30_DAYS)
    assert today.orders == 0
    assert week.orders == 0
    assert month.orders == 1
    assert month.revenue == created.json()['total_amount']


def test_export_filename_and_period_labels():
    start = date(2026, 8, 1)
    end = date(2026, 8, 10)
    assert export_filename(ReportPeriod.TODAY, start, end) == 'sales-report-today.pdf'
    assert export_filename(ReportPeriod.LAST_7_DAYS, start, end) == 'sales-report-last-7-days.pdf'
    assert export_filename(ReportPeriod.LAST_30_DAYS, start, end) == 'sales-report-last-30-days.pdf'
    assert export_filename(ReportPeriod.CUSTOM, start, end) == 'sales-report-2026-08-01-to-2026-08-10.pdf'
    assert period_label(ReportPeriod.TODAY, start, end) == 'Today'
    assert period_label(ReportPeriod.LAST_7_DAYS, start, end) == 'Last 7 Days'
    assert period_label(ReportPeriod.LAST_30_DAYS, start, end) == 'Last 30 Days'
    assert period_label(ReportPeriod.CUSTOM, start, end) == '01 Aug 2026 - 10 Aug 2026'


def test_render_pdf_omits_internal_ids():
    report = SalesReportExport(
        title=TITLE,
        period_label='Today',
        scope_label='Franchise: Example Outlet',
        generated_label='22 Aug 2026 10:30 AM UTC',
        filename='sales-report-today.pdf',
        revenue=100,
        orders=1,
        avg_order=100,
        items_sold=2,
        daily=[('22 Aug 2026', 100)],
        products=[('Nimbu Pudina', 2, 44)],
        payments=[('Cash', 100), ('UPI', 0), ('Card', 0)],
        bills=[('RS-1001', '22 Aug 2026 10:30 AM', 100, 'Cash')],
    )
    content = render_sales_report_pdf(report)
    assert content.startswith(b'%PDF')
    assert BRAND_NAME.encode() in content
    assert b'Sales Report' in content
    assert b'Summary' in content
    assert b'Daily Revenue' in content
    assert b'Top Products' in content
    assert b'Payment Methods' in content
    assert b'Recent Bills' in content
    assert b'Product Sales Details' in content
    assert EMPTY_PRODUCT_SALES.encode() in content
    assert b'RS-1001' in content
    assert b'Example Outlet' in content
    assert str(FRANCHISE_A).encode() not in content
    assert b'/api/v1' not in content
    assert b'stack' not in content.lower()


def _sample_export(**overrides) -> SalesReportExport:
    payload = dict(
        title=TITLE,
        period_label='Today',
        scope_label='Franchise: Example Outlet',
        generated_label='22 Aug 2026 10:30 AM UTC',
        filename='sales-report-today.pdf',
        revenue=100,
        orders=1,
        avg_order=100,
        items_sold=2,
        daily=[('22 Aug 2026', 100)],
        products=[('Nimbu Pudina', 2, 44)],
        payments=[('Cash', 100), ('UPI', 0), ('Card', 0)],
        bills=[('RS-1001', '22 Aug 2026 10:30 AM', 100, 'Cash')],
        product_details=[],
    )
    payload.update(overrides)
    return SalesReportExport(**payload)


def test_pdf_logo_is_backend_runtime_asset():
    pdf_source = Path(__file__).resolve().parents[1] / 'app' / 'modules' / 'reports' / 'pdf.py'
    source = pdf_source.read_text(encoding='utf-8')
    assert 'frontend/public' not in source
    assert "Path(__file__).resolve().parent / 'assets'" in source
    logo = brand_logo_path()
    assert logo is not None
    assert logo.parent.name == 'assets'
    assert logo.parent.parent.name == 'reports'


def test_pdf_contains_realstick_branding_and_logo():
    logo = brand_logo_path()
    assert logo is not None
    assert logo.name == 'realstick_logo.jpeg'
    assert 'frontend' not in str(logo).replace('\\', '/')
    assert (logo.parent / logo.name).is_file()
    content = render_sales_report_pdf(_sample_export())
    assert BRAND_NAME.encode() in content
    assert b'Sales Report' in content
    assert b'/Image' in content
    assert b'DCTDecode' in content


def test_pdf_generates_when_logo_asset_is_missing(monkeypatch):
    monkeypatch.setattr('app.modules.reports.pdf.brand_logo_path', lambda: None)
    content = render_sales_report_pdf(_sample_export())
    assert content.startswith(b'%PDF')
    assert BRAND_NAME.encode() in content
    assert b'Sales Report' in content
    assert b'Product Sales Details' in content


def test_pdf_product_sales_details_columns_and_rows():
    report = _sample_export(
        product_details=[
            ('Mango Stick', 'Seasonal', 'UPI', 120),
            ('Orange Stick', 'Citrus', 'Cash', 100),
        ]
    )
    content = render_sales_report_pdf(report)
    assert b'Product Sales Details' in content
    assert b'S.No' in content
    assert b'Item' in content
    assert b'Category' in content
    assert b'Payment Method' in content
    assert b'Price' in content
    assert b'Mango Stick' in content
    assert b'Seasonal' in content
    assert b'UPI' in content
    assert b'Rs. 120.00' in content
    assert b'Orange Stick' in content
    assert EMPTY_PRODUCT_SALES.encode() not in content
    assert content.rfind(b'Product Sales Details') > content.rfind(b'Recent Bills')


def test_empty_product_sales_details_has_no_blank_table():
    content = render_sales_report_pdf(_sample_export(product_details=[]))
    assert b'Product Sales Details' in content
    assert EMPTY_PRODUCT_SALES.encode() in content
    assert b'S.No' not in content.split(b'Product Sales Details', 1)[1]


def test_multiple_order_items_produce_multiple_product_rows(client, auth_header_factory):
    _assign_orange_a(client, auth_header_factory, selling_price=40)
    created = _checkout(
        client,
        _employee(auth_header_factory),
        items=[
            {'product_id': str(PRODUCT_NIMBU), 'quantity': 1},
            {'product_id': str(PRODUCT_ORANGE), 'quantity': 1},
        ],
        payment_method='UPI',
    )
    assert created.status_code == 201
    payload = ReportsService().build_export_payload(_owner_profile(), ReportPeriod.TODAY)
    names = [row[0] for row in payload.product_details]
    payments = [row[2] for row in payload.product_details]
    prices = [row[3] for row in payload.product_details]
    categories = [row[1] for row in payload.product_details]
    assert len(payload.product_details) == 2
    assert names.count('Nimbu Pudina') == 1
    assert names.count('Nagpur Orange') == 1
    assert payments == ['UPI', 'UPI']
    assert 22.0 in prices
    assert 40.0 in prices
    assert 'Zest Collection' in categories
    assert 'Garden Collection' in categories

    response = client.get(EXPORT, headers=_owner(auth_header_factory), params={'period': 'today'})
    assert response.status_code == 200
    assert b'Nimbu Pudina' in response.content
    assert b'Nagpur Orange' in response.content
    assert b'Zest Collection' in response.content
    assert b'Garden Collection' in response.content
    assert b'S.No' in response.content
    assert b'Payment Method' in response.content
    assert format_inr(22).encode() in response.content
    assert format_inr(40).encode() in response.content


def test_payment_method_is_associated_with_each_order_item(client, auth_header_factory):
    cash = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    _assign_orange_a(client, auth_header_factory, selling_price=40)
    upi = _checkout(
        client,
        _employee(auth_header_factory),
        items=[{'product_id': str(PRODUCT_ORANGE), 'quantity': 1}],
        payment_method='UPI',
    )
    assert cash.status_code == 201
    assert upi.status_code == 201
    payload = ReportsService().build_export_payload(_owner_profile(), ReportPeriod.TODAY)
    by_item = {row[0]: row for row in payload.product_details}
    assert by_item['Nimbu Pudina'][2] == 'Cash'
    assert by_item['Nimbu Pudina'][3] == cash.json()['items'][0]['unit_price']
    assert by_item['Nagpur Orange'][2] == 'UPI'
    assert by_item['Nagpur Orange'][3] == upi.json()['items'][0]['unit_price']


def test_product_details_use_historical_billed_price_not_master_or_current(
    client, auth_header_factory
):
    created = _checkout(
        client,
        _employee(auth_header_factory),
        items=[{'product_id': str(PRODUCT_NIMBU), 'quantity': 2}],
        payment_method='CARD',
    )
    assert created.status_code == 201
    billed = created.json()['items'][0]['unit_price']
    assert billed == 22

    renamed = client.patch(
        f'/api/v1/admin/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'name': 'Nimbu Pudina Deluxe', 'price': 500},
    )
    assert renamed.status_code == 200
    client.patch(
        f'/api/v1/admin/franchises/{FRANCHISE_A}/products/{PRODUCT_NIMBU}',
        headers=_admin(auth_header_factory),
        json={'selling_price': 40},
    )

    payload = ReportsService().build_export_payload(_owner_profile(), ReportPeriod.TODAY)
    assert payload.product_details == [('Nimbu Pudina', 'Zest Collection', 'Card', 22.0)]
    response = client.get(EXPORT, headers=_owner(auth_header_factory), params={'period': 'today'})
    assert response.status_code == 200
    assert b'Nimbu Pudina' in response.content
    assert b'Nimbu Pudina Deluxe' not in response.content
    assert format_inr(22).encode() in response.content
    assert format_inr(40).encode() not in response.content
    assert format_inr(500).encode() not in response.content
    assert format_inr(100).encode() not in response.content


def test_admin_product_details_include_all_franchises(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory, selling_price=30)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='UPI')
    assert other.status_code == 201

    admin_payload = ReportsService().build_export_payload(
        _admin_profile(),
        ReportPeriod.TODAY,
        franchise_id=FRANCHISE_A,
    )
    owner_payload = ReportsService().build_export_payload(_owner_profile(), ReportPeriod.TODAY)
    assert admin_payload.scope_label == SCOPE_ALL_FRANCHISES
    assert len(admin_payload.product_details) == 2
    prices = sorted(row[3] for row in admin_payload.product_details)
    assert prices == [22.0, 30.0]
    methods = {row[2] for row in admin_payload.product_details}
    assert methods == {'Cash', 'UPI'}
    assert len(owner_payload.product_details) == 1
    assert owner_payload.product_details[0][3] == own.json()['items'][0]['unit_price']


def test_owner_product_details_stay_franchise_scoped(client, auth_header_factory):
    own = _checkout(client, _employee(auth_header_factory), payment_method='CASH')
    assert own.status_code == 201
    _assign_nimbu_b(client, auth_header_factory, selling_price=30)
    other = _checkout(client, _employee_b(auth_header_factory), payment_method='CARD')
    assert other.status_code == 201

    payload = ReportsService().build_export_payload(
        _owner_profile(),
        ReportPeriod.TODAY,
        franchise_id=FRANCHISE_B,
    )
    assert payload.scope_label.startswith('Franchise:')
    assert SCOPE_ALL_FRANCHISES not in payload.scope_label
    assert payload.product_details == [('Nimbu Pudina', 'Zest Collection', 'Cash', 22.0)]
    assert all(row[3] != other.json()['items'][0]['unit_price'] for row in payload.product_details)


def test_custom_date_range_filters_product_rows(client, auth_header_factory, fake_db):
    _seed_order(
        fake_db,
        status='COMPLETED',
        franchise_id=FRANCHISE_A,
        total_amount=22,
        payment_method='CASH',
        completed_at=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc).isoformat(),
        items=[{'product_name_snapshot': 'In Range Stick', 'unit_price': 22, 'quantity': 1}],
    )
    _seed_order(
        fake_db,
        status='COMPLETED',
        franchise_id=FRANCHISE_A,
        total_amount=99,
        payment_method='UPI',
        completed_at=datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc).isoformat(),
        items=[{'product_name_snapshot': 'Outside Stick', 'unit_price': 99, 'quantity': 1}],
    )
    payload = ReportsService().build_export_payload(
        _owner_profile(),
        ReportPeriod.CUSTOM,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 10),
    )
    names = [row[0] for row in payload.product_details]
    assert names == ['In Range Stick']
    assert payload.product_details[0][2] == 'Cash'
    assert payload.product_details[0][3] == 22.0

    response = client.get(
        EXPORT,
        headers=_owner(auth_header_factory),
        params=_custom_params('2026-08-01', '2026-08-10'),
    )
    assert response.status_code == 200
    assert b'In Range Stick' in response.content
    assert b'Outside Stick' not in response.content


def test_custom_range_product_rows_include_end_date(client, auth_header_factory, fake_db):
    _seed_order(
        fake_db,
        status='COMPLETED',
        franchise_id=FRANCHISE_A,
        total_amount=25,
        payment_method='UPI',
        completed_at=datetime(2026, 8, 10, 23, 59, 59, tzinfo=timezone.utc).isoformat(),
        items=[{'product_name_snapshot': 'End Day Stick', 'unit_price': 25, 'quantity': 1}],
    )
    _seed_order(
        fake_db,
        status='COMPLETED',
        franchise_id=FRANCHISE_A,
        total_amount=70,
        payment_method='CARD',
        completed_at=datetime(2026, 8, 11, 0, 0, tzinfo=timezone.utc).isoformat(),
        items=[{'product_name_snapshot': 'Next Day Stick', 'unit_price': 70, 'quantity': 1}],
    )
    payload = ReportsService().build_export_payload(
        _owner_profile(),
        ReportPeriod.CUSTOM,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 10),
    )
    names = [row[0] for row in payload.product_details]
    assert names == ['End Day Stick']
    assert payload.product_details[0][3] == 25.0
    response = client.get(
        EXPORT,
        headers=_owner(auth_header_factory),
        params=_custom_params('2026-08-01', '2026-08-10'),
    )
    assert response.status_code == 200
    assert b'End Day Stick' in response.content
    assert b'Next Day Stick' not in response.content


def test_empty_product_sales_export_message(client, auth_header_factory):
    response = client.get(EXPORT, headers=_owner(auth_header_factory), params={'period': 'today'})
    payload = ReportsService().build_export_payload(_owner_profile(), ReportPeriod.TODAY)
    assert response.status_code == 200
    assert payload.product_details == []
    assert b'Product Sales Details' in response.content
    assert EMPTY_PRODUCT_SALES.encode() in response.content
    assert b'S.No' not in response.content.split(b'Product Sales Details', 1)[1]


def test_non_latin_product_name_does_not_crash_pdf():
    report = _sample_export(
        product_details=[('मैंगो स्टिक', 'सीजनल', 'UPI', 120)],
    )
    content = render_sales_report_pdf(report)
    assert content.startswith(b'%PDF')
    assert b'Product Sales Details' in content
    assert format_inr(120).encode() in content
