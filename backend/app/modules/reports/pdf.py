"""PDF rendering for sales-report export.

Business calculations live in ReportsService. This module only formats the
already-computed report payload into a downloadable PDF.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import Align, TableHeadingsDisplay, VAlign, WrapMode
from fpdf.fonts import FontFace

from app.modules.reports.dates import ReportPeriod

BRAND_NAME = 'RealStick'
TITLE = 'Sales Report'
SCOPE_ALL_FRANCHISES = 'All Franchises'
BRAND_GREEN = (26, 122, 74)
HEADER_FILL = (230, 244, 236)
MUTED = (90, 90, 84)
LINE = (224, 221, 213)
ASSETS_DIR = Path(__file__).resolve().parent / 'assets'
# Official supplied logo is JPEG; runtime path is this module's assets directory.
LOGO_FILENAMES = ('realstick_logo.jpeg', 'realstick_logo.jpg', 'realstick_logo.png')
LOGO_MAX_MM = 18
MONTHS = (
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
)
PAYMENT_LABELS = {
    'CASH': 'Cash',
    'UPI': 'UPI',
    'CARD': 'Card',
}
EMPTY_PRODUCT_SALES = 'No product sales found for the selected period.'


@dataclass(frozen=True)
class SalesReportExport:
    title: str
    period_label: str
    scope_label: str
    generated_label: str
    filename: str
    revenue: float
    orders: int
    avg_order: int
    items_sold: int
    daily: list[tuple[str, float]]
    products: list[tuple[str, int, float]]
    payments: list[tuple[str, float]]
    bills: list[tuple[str, str, float, str]]
    product_details: list[tuple[str, str, str, float]] = field(default_factory=list)


def brand_logo_path() -> Path | None:
    for name in LOGO_FILENAMES:
        path = ASSETS_DIR / name
        try:
            if path.is_file() and path.stat().st_size > 0:
                return path
        except OSError:
            continue
    return None


def format_display_date(value: date) -> str:
    return f'{value.day:02d} {MONTHS[value.month - 1]} {value.year}'


def format_generated_at(value: datetime | None = None) -> str:
    moment = value or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    hour = moment.strftime('%I').lstrip('0') or '12'
    return f'{format_display_date(moment.date())} {hour}:{moment.strftime("%M %p")} UTC'


def format_bill_when(value: datetime | str | None) -> str:
    if value is None:
        return '-'
    parsed: datetime
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).replace('Z', '+00:00')
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return '-'
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    hour = parsed.strftime('%I').lstrip('0') or '12'
    return f'{format_display_date(parsed.date())} {hour}:{parsed.strftime("%M %p")}'


def payment_label(method: str | None) -> str:
    if not method:
        return '-'
    return PAYMENT_LABELS.get(method, method)


def period_label(period: ReportPeriod, start: date, end: date) -> str:
    if period == ReportPeriod.TODAY:
        return 'Today'
    if period == ReportPeriod.LAST_7_DAYS:
        return 'Last 7 Days'
    if period == ReportPeriod.LAST_30_DAYS:
        return 'Last 30 Days'
    return f'{format_display_date(start)} - {format_display_date(end)}'


def export_filename(period: ReportPeriod, start: date, end: date) -> str:
    if period == ReportPeriod.TODAY:
        return 'sales-report-today.pdf'
    if period == ReportPeriod.LAST_7_DAYS:
        return 'sales-report-last-7-days.pdf'
    if period == ReportPeriod.LAST_30_DAYS:
        return 'sales-report-last-30-days.pdf'
    return f'sales-report-{start.isoformat()}-to-{end.isoformat()}.pdf'


def format_inr(amount: float | int) -> str:
    value = float(amount)
    quantized = f'{abs(value):.2f}'
    whole, frac = quantized.split('.')
    grouped = _indian_group(whole)
    sign = '-' if value < 0 else ''
    return f'Rs. {sign}{grouped}.{frac}'


def _indian_group(whole: str) -> str:
    if len(whole) <= 3:
        return whole
    last3 = whole[-3:]
    rest = whole[:-3]
    parts: list[str] = []
    while len(rest) > 2:
        parts.append(rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.append(rest)
    return ','.join(reversed(parts)) + ',' + last3


def latin1(text: str) -> str:
    replacements = {
        '\u2013': '-',
        '\u2014': '-',
        '\u2018': "'",
        '\u2019': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u20b9': 'Rs.',
    }
    cleaned = text
    for src, dst in replacements.items():
        cleaned = cleaned.replace(src, dst)
    return cleaned.encode('latin-1', 'replace').decode('latin-1')


def content_disposition(filename: str) -> str:
    safe = latin1(filename).replace('"', '')
    return f'attachment; filename="{safe}"'


class _SalesReportPdf(FPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_fill_color(*BRAND_GREEN)
        self.rect(0, 0, self.w, 12, 'F')
        self.set_xy(16, 3)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(255, 255, 255)
        self.cell(self.epw, 6, latin1(f'{BRAND_NAME}  |  {TITLE}'), align='L')
        self.set_text_color(26, 26, 24)
        self.set_y(18)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*MUTED)
        self.cell(self.epw, 8, f'Page {self.page_no()}', align='C')


def render_sales_report_pdf(report: SalesReportExport) -> bytes:
    pdf = _SalesReportPdf(format='A4', unit='mm')
    pdf.compress = False
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(16, 16, 16)
    pdf.add_page()
    pdf.set_font('Helvetica', '', 10)

    _draw_branding(pdf)
    _meta_row(pdf, 'Period', report.period_label)
    _meta_row(pdf, 'Scope', report.scope_label)
    _meta_row(pdf, 'Generated', report.generated_label)
    pdf.ln(4)

    _section(pdf, 'Summary')
    summary_rows = [
        ('Revenue', format_inr(report.revenue)),
        ('Orders', str(report.orders)),
        ('Avg Order', format_inr(report.avg_order)),
        ('Items Sold', str(report.items_sold)),
    ]
    _table(pdf, ('Metric', 'Value'), summary_rows, (90, 88))

    _section(pdf, 'Daily Revenue')
    if report.daily:
        _table(
            pdf,
            ('Date', 'Revenue'),
            [(day, format_inr(amount)) for day, amount in report.daily],
            (90, 88),
        )
    else:
        _empty(pdf, 'No daily revenue for this period.')

    _section(pdf, 'Top Products')
    if report.products:
        _table(
            pdf,
            ('Product', 'Quantity', 'Revenue'),
            [(name, str(qty), format_inr(amount)) for name, qty, amount in report.products],
            (98, 30, 50),
        )
    else:
        _empty(pdf, 'No sales yet')

    _section(pdf, 'Payment Methods')
    _table(
        pdf,
        ('Method', 'Amount'),
        [(method, format_inr(amount)) for method, amount in report.payments],
        (90, 88),
    )

    _section(pdf, 'Recent Bills')
    if report.bills:
        _table(
            pdf,
            ('Bill No.', 'Completed', 'Amount', 'Payment'),
            [
                (number, when, format_inr(amount), method)
                for number, when, amount, method in report.bills
            ],
            (40, 62, 38, 38),
        )
    else:
        _empty(pdf, 'No bills yet')

    _section(pdf, 'Product Sales Details')
    if report.product_details:
        _product_sales_table(pdf, report.product_details)
    else:
        _empty(pdf, EMPTY_PRODUCT_SALES)

    return bytes(pdf.output())


def _draw_branding(pdf: FPDF) -> None:
    logo = brand_logo_path()
    if logo is not None:
        try:
            start_y = pdf.get_y()
            pdf.image(
                str(logo),
                x=pdf.l_margin,
                y=start_y,
                w=LOGO_MAX_MM,
                h=LOGO_MAX_MM,
                keep_aspect_ratio=True,
            )
            pdf.set_y(start_y + LOGO_MAX_MM + 3)
        except Exception:
            pass

    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(*BRAND_GREEN)
    pdf.cell(pdf.epw, 8, latin1(BRAND_NAME), align='L')
    pdf.ln(8)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(26, 26, 24)
    pdf.cell(pdf.epw, 7, latin1(TITLE), align='L')
    pdf.ln(10)


def _meta_row(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(28, 6, latin1(f'{label}:'), align='L')
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(26, 26, 24)
    pdf.cell(pdf.epw - 28, 6, latin1(value), align='L')
    pdf.ln(6)


def _section(pdf: FPDF, title: str) -> None:
    _ensure_space(pdf, 18)
    pdf.ln(2)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*BRAND_GREEN)
    pdf.cell(pdf.epw, 7, latin1(title), align='L')
    pdf.ln(8)
    pdf.set_draw_color(*LINE)
    pdf.set_text_color(26, 26, 24)


def _empty(pdf: FPDF, message: str) -> None:
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(pdf.epw, 6, latin1(message), align='L')
    pdf.ln(8)
    pdf.set_text_color(26, 26, 24)


def _table(pdf: FPDF, headers: tuple[str, ...], rows: list[tuple[str, ...]], widths: tuple[float, ...]) -> None:
    _ensure_space(pdf, 16)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(*HEADER_FILL)
    pdf.set_text_color(*BRAND_GREEN)
    pdf.set_draw_color(*LINE)
    for header, width in zip(headers, widths, strict=True):
        pdf.cell(width, 7, latin1(header), border=1, fill=True, align='L')
    pdf.ln(7)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(26, 26, 24)
    for row in rows:
        _ensure_space(pdf, 8)
        for value, width in zip(row, widths, strict=True):
            pdf.cell(width, 6.5, latin1(value), border=1, align='L')
        pdf.ln(6.5)
    pdf.ln(3)


def _product_sales_table(pdf: FPDF, rows: list[tuple[str, str, str, float]]) -> None:
    _ensure_space(pdf, 20)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(26, 26, 24)
    pdf.set_draw_color(*LINE)
    headings = FontFace(
        emphasis='BOLD',
        size_pt=8,
        color=BRAND_GREEN,
        fill_color=HEADER_FILL,
    )
    usable = pdf.epw
    with pdf.table(
        width=usable,
        col_widths=(usable * 0.08, usable * 0.32, usable * 0.24, usable * 0.20, usable * 0.16),
        text_align=(Align.C, Align.L, Align.L, Align.L, Align.R),
        align=Align.L,
        headings_style=headings,
        line_height=5,
        padding=1.2,
        repeat_headings=TableHeadingsDisplay.ON_TOP_OF_EVERY_PAGE,
        wrapmode=WrapMode.CHAR,
        v_align=VAlign.M,
    ) as table:
        header = table.row()
        for title in ('S.No', 'Item', 'Category', 'Payment Method', 'Price'):
            header.cell(latin1(title))
        for index, (item, category, method, price) in enumerate(rows, start=1):
            row = table.row()
            row.cell(str(index))
            row.cell(latin1(item))
            row.cell(latin1(category))
            row.cell(latin1(method))
            row.cell(latin1(format_inr(price)))
    pdf.ln(3)


def _ensure_space(pdf: FPDF, needed: float) -> None:
    if pdf.get_y() + needed > pdf.h - pdf.b_margin:
        pdf.add_page()
