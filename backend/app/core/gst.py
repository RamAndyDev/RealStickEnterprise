"""GST rate helpers. Total GST is stored; CGST/SGST are always an even 50/50 split."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

TWOPLACES = Decimal('0.01')
GST_MAX_RATE = Decimal('40.00')


class GstConfigError(ValueError):
    """Raised when a GST rate cannot be split evenly into CGST and SGST."""


def money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def split_gst_rate(rate: object) -> tuple[Decimal, Decimal]:
    """Return (cgst_rate, sgst_rate) as exactly 50% of total GST each."""
    gst_rate = money(rate)
    cgst_rate = money(gst_rate / 2)
    sgst_rate = money(gst_rate / 2)
    if cgst_rate + sgst_rate != gst_rate:
        raise GstConfigError('GST rate must split evenly into CGST and SGST')
    return cgst_rate, sgst_rate
