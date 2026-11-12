import { Button } from '../../components/ui';
import type { PosCartLine, PosOffer, PosPaymentMethod } from '../../types/pos';
import { formatINR, previewTotals } from '../../types/pos';

const PAYMENTS: { id: PosPaymentMethod; label: string; icon: string }[] = [
  { id: 'UPI', label: 'UPI', icon: '📲' },
  { id: 'CASH', label: 'Cash', icon: '💵' },
  { id: 'CARD', label: 'Card', icon: '💳' },
];

export function CartPanel({
  cashierName,
  franchiseName,
  lines,
  gstRate,
  offers,
  selectedOfferId,
  paymentMethod,
  phone,
  success,
  onIncrease,
  onDecrease,
  onRemove,
  onClear,
  onSelectOffer,
  onPaymentMethod,
  onPhone,
  onCheckout,
}: {
  cashierName: string;
  franchiseName: string;
  lines: PosCartLine[];
  gstRate: number | null;
  offers: PosOffer[];
  selectedOfferId: string | null;
  paymentMethod: PosPaymentMethod;
  phone: string;
  success: string | null;
  onIncrease: (productId: string) => void;
  onDecrease: (productId: string) => void;
  onRemove: (productId: string) => void;
  onClear: () => void;
  onSelectOffer: (offerId: string | null) => void;
  onPaymentMethod: (method: PosPaymentMethod) => void;
  onPhone: (value: string) => void;
  onCheckout: () => void;
}) {
  const selectedOffer = offers.find((offer) => offer.id === selectedOfferId) ?? null;
  const discountPercent = selectedOffer?.discount_value ?? 0;
  const totals = previewTotals(lines, discountPercent, gstRate);

  return (
    <aside className="flex max-h-[46vh] w-full min-h-0 flex-col overflow-hidden border-t border-[#E0DDD5] bg-white md:max-h-none md:h-full md:w-64 md:shrink-0 md:border-l md:border-t-0 lg:w-72 xl:w-80">
      <div className="shrink-0 bg-[#0D4F2E] px-3.5 py-3 text-white">
        <div className="flex items-center justify-between gap-2">
          <div className="text-[16px] font-bold leading-5">Current Bill</div>
          {lines.length ? (
            <button
              type="button"
              onClick={onClear}
              className="min-h-11 px-2 text-[12px] text-white/55 hover:text-white lg:min-h-0 lg:text-[10px]"
            >
              Clear
            </button>
          ) : null}
        </div>
        <div className="mt-0.5 text-[10px] text-white/55">
          {cashierName} · {franchiseName}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-2.5">
        <div className="py-1.5">
        {!lines.length ? (
          <div className="px-3.5 py-7 text-center text-[#8A8A84]">
            <div className="mb-1 text-[26px]">🍡</div>
            <div className="text-[12px]">Add items from the menu</div>
          </div>
        ) : null}
        {lines.map((line) => (
          <div key={line.product_id} className="border-b border-[#E0DDD5] py-2">
            <div className="flex min-w-0 items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="break-words text-[14px] font-semibold leading-snug text-[#1A1A18]">
                  {line.name}
                </div>
                <div className="mt-0.5 text-[13px] leading-5 text-[#6F706A]">
                  {formatINR(line.selling_price)} each
                </div>
              </div>
              <button
                type="button"
                onClick={() => onRemove(line.product_id)}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-[21px] leading-none text-[#8A8A84] hover:bg-[#FFF5F5] hover:text-[#C00000]"
                aria-label={`Remove ${line.name}`}
              >
                ×
              </button>
            </div>
            <div className="mt-1 flex min-w-0 items-center justify-between gap-2">
              <div className="flex shrink-0 items-center gap-0">
                <button
                  type="button"
                  onClick={() => onDecrease(line.product_id)}
                  className="flex h-11 w-11 items-center justify-center rounded-[5px] border border-[#E0DDD5] bg-[#FDFAF4] text-[18px]"
                  aria-label={`Decrease ${line.name}`}
                >
                  −
                </button>
                <span className="min-w-[28px] text-center text-[14px] font-semibold tabular-nums">
                  {line.quantity}
                </span>
                <button
                  type="button"
                  onClick={() => onIncrease(line.product_id)}
                  className="flex h-11 w-11 items-center justify-center rounded-[5px] border border-[#1A7A4A] bg-[#E6F4EC] text-[18px] text-[#1A7A4A]"
                  aria-label={`Increase ${line.name}`}
                >
                  +
                </button>
              </div>
              <div className="min-w-0 flex-1 text-right text-[14px] font-semibold leading-5 text-[#1A1A18] tabular-nums">
                {formatINR(line.selling_price * line.quantity)}
              </div>
            </div>
          </div>
        ))}
        </div>

        <div className="border-t border-[#E0DDD5] px-2.5 pb-2.5 pt-2">
        {offers.length ? (
          <>
            <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
              Available Offers
            </div>
            <div className="mb-2 space-y-1.5">
              {offers.map((offer) => {
                const selected = selectedOfferId === offer.id;
                return (
                  <div
                    key={offer.id}
                    className="rounded-lg border px-2 py-1.5"
                    style={{
                      borderColor: selected ? '#E8621A' : '#E0DDD5',
                      background: selected ? '#FFF4ED' : '#fff',
                    }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="text-[12px] font-semibold text-[#1A1A18]">{offer.name}</div>
                        <div className="text-[10px] font-semibold text-[#E8621A]">
                          {Number(offer.discount_value).toFixed(0)}% OFF
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => onSelectOffer(selected ? null : offer.id)}
                        className="min-h-11 shrink-0 rounded-full px-3 text-[12px] font-semibold lg:min-h-0 lg:px-2 lg:py-0.5 lg:text-[9px]"
                        aria-label={selected ? `Remove ${offer.name}` : `Apply ${offer.name}`}
                        style={{
                          background: selected ? '#E8621A' : 'transparent',
                          color: selected ? '#fff' : '#E8621A',
                          border: '1px solid #E8621A',
                        }}
                      >
                        {selected ? 'Applied' : 'Apply'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        ) : null}

        <div className="mb-1.5 text-[12px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
          Payment
        </div>
        <div className="mb-2 flex gap-1.5">
          {PAYMENTS.map((method) => {
            const selected = paymentMethod === method.id;
            return (
              <button
                key={method.id}
                type="button"
                onClick={() => onPaymentMethod(method.id)}
                className="flex min-h-11 min-w-0 flex-1 flex-nowrap items-center justify-center gap-1 whitespace-nowrap rounded-[7px] px-1.5 text-[13px] font-semibold leading-none"
                style={{
                  border: `2px solid ${selected ? '#1A7A4A' : '#E0DDD5'}`,
                  background: selected ? '#E6F4EC' : '#fff',
                  color: selected ? '#1A7A4A' : '#4A4A46',
                }}
              >
                <span aria-hidden="true" className="shrink-0">{method.icon}</span>
                <span>{method.label}</span>
              </button>
            );
          })}
        </div>
        <input
          placeholder="Customer phone (optional)"
          value={phone}
          onChange={(e) => onPhone(e.target.value)}
          className="mb-2 w-full rounded-[7px] border border-[#E0DDD5] px-2.5 py-2 text-[14px] outline-none"
        />

        <div className="mb-2 rounded-lg bg-[#FDFAF4] px-2.5 py-2">
          <div className="mb-0.5 flex justify-between text-[12px] text-[#4A4A46]">
            <span>Subtotal</span>
            <span>{formatINR(totals.subtotal)}</span>
          </div>
          {selectedOffer ? (
            <div className="mb-0.5 text-[11px] text-[#E8621A]">
              {selectedOffer.name} · {Number(selectedOffer.discount_value).toFixed(0)}% OFF
            </div>
          ) : null}
          <div className="mb-0.5 flex justify-between text-[12px] text-[#E8621A]">
            <span>Discount</span>
            <span>{totals.discount > 0 ? `−${formatINR(totals.discount)}` : formatINR(0)}</span>
          </div>
          <div className="mb-0.5 flex justify-between text-[12px] text-[#4A4A46]">
            <span>Taxable Amount</span>
            <span>{formatINR(totals.taxable)}</span>
          </div>
          <div className="mb-0.5 flex justify-between text-[12px] text-[#4A4A46]">
            <span>CGST @ {gstRate == null ? '—' : `${totals.cgstRate.toFixed(2)}%`}</span>
            <span>{gstRate == null ? '—' : formatINR(totals.cgst)}</span>
          </div>
          <div className="mb-0.5 flex justify-between text-[12px] text-[#4A4A46]">
            <span>SGST @ {gstRate == null ? '—' : `${totals.sgstRate.toFixed(2)}%`}</span>
            <span>{gstRate == null ? '—' : formatINR(totals.sgst)}</span>
          </div>
          <div className="mb-0.5 flex justify-between text-[12px] text-[#4A4A46]">
            <span>Total GST</span>
            <span>{gstRate == null ? '—' : formatINR(totals.gst)}</span>
          </div>
          <div className="mt-0.5 flex justify-between border-t border-[#E0DDD5] pt-1 text-[16px] font-bold text-[#1A1A18]">
            <span>Total</span>
            <span className="text-[#1A7A4A]">{formatINR(totals.total)}</span>
          </div>
        </div>

        {gstRate == null ? (
          <div className="mb-2 rounded-[7px] bg-[#FFF5F5] px-2.5 py-1.5 text-center text-[12px] text-[#C00000]">
            GST is not configured. Billing is unavailable.
          </div>
        ) : null}
        {success ? (
          <div className="mb-2 rounded-[7px] bg-[#E6F4EC] px-2.5 py-1.5 text-center text-[12px] font-semibold text-[#1A7A4A]">
            {success}
          </div>
        ) : null}
        <Button
          className="min-h-11 w-full py-2.5 text-[14px]"
          disabled={!lines.length || gstRate == null}
          onClick={onCheckout}
        >
          🖨️ Bill & Print Receipt
        </Button>
        </div>
      </div>
    </aside>
  );
}
