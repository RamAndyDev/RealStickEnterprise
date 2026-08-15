import { Button } from '../../components/ui';
import type { PosPaymentMethod } from '../../types/pos';
import { formatINR } from '../../types/pos';

const METHOD_LABEL: Record<PosPaymentMethod, string> = {
  UPI: 'UPI',
  CASH: 'Cash',
  CARD: 'Card',
};

export function CheckoutModal({
  total,
  paymentMethod,
  submitting,
  error,
  onConfirm,
  onClose,
}: {
  total: number;
  paymentMethod: PosPaymentMethod;
  submitting: boolean;
  error: string | null;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Confirm payment"
        className="w-full max-w-[420px] rounded-2xl bg-white shadow-[0_8px_40px_rgba(0,0,0,.25)]"
      >
        <div className="flex items-center justify-between border-b border-[#E0DDD5] px-5 py-4">
          <h2 className="text-[15px] font-bold text-[#1A1A18]">Confirm payment</h2>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="text-[22px] leading-none text-[#8A8A84] hover:text-[#1A1A18]"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="px-5 py-4">
          <p className="text-sm text-[#4A4A46]">
            Confirm {METHOD_LABEL[paymentMethod]} payment of{' '}
            <span className="font-semibold text-[#1A1A18]">{formatINR(total)}</span>?
          </p>
          <p className="mt-2 text-[12px] text-[#8A8A84]">
            The order will be completed and a thermal receipt will open for printing.
          </p>
          {error ? (
            <div className="mt-3 rounded-lg bg-[#FFF5F5] px-3 py-2 text-[12px] text-[#C00000]">
              {error}
            </div>
          ) : null}
          <div className="mt-5 flex flex-col-reverse justify-end gap-2 sm:flex-row">
            <Button variant="muted" className="min-h-11" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button className="min-h-11" onClick={onConfirm} disabled={submitting}>
              {submitting ? 'Completing…' : 'Confirm payment'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
