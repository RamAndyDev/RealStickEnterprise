import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { Badge, Button, ErrorBanner, LoadingBlock } from '../../components/ui';
import { fetchCompletedOrder } from '../../lib/ordersApi';
import { apiErrorMessage } from '../franchises/status';
import { formatINR } from '../../types/pos';
import { formatBillDateTime, paymentLabel } from '../../types/orders';

function SummaryRow({
  label,
  value,
  emphasize = false,
}: {
  label: string;
  value: string;
  emphasize?: boolean;
}) {
  return (
    <div className={`flex items-center justify-between gap-4 py-1.5 ${emphasize ? 'font-bold' : ''}`}>
      <span className={emphasize ? 'text-[#1A1A18]' : 'text-[#8A8A84]'}>{label}</span>
      <span className={emphasize ? 'text-[#1A7A4A]' : 'text-[#1A1A18]'}>{value}</span>
    </div>
  );
}

export function BillDetailPage() {
  const { orderId } = useParams();

  const detailQuery = useQuery({
    queryKey: ['completed-bill', orderId],
    queryFn: () => fetchCompletedOrder(orderId!),
    enabled: Boolean(orderId),
  });

  if (!orderId) {
    return <ErrorBanner message="Missing bill id." />;
  }
  if (detailQuery.isLoading) {
    return <LoadingBlock label="Loading bill…" />;
  }
  if (detailQuery.isError || !detailQuery.data) {
    return (
      <div className="mx-auto max-w-3xl">
        <ErrorBanner message={apiErrorMessage(detailQuery.error, 'Unable to load bill.')} />
        <Link to="/bills" className="mt-4 inline-block text-sm text-[#1A7A4A]">
          ← Back to Bills
        </Link>
      </div>
    );
  }

  const bill = detailQuery.data;
  const when = formatBillDateTime(bill.completed_at || bill.created_at);
  const offerLabel = bill.offer_name
    ? bill.discount_value != null
      ? `Offer: ${bill.offer_name} (${Number(bill.discount_value).toFixed(0)}%)`
      : `Offer: ${bill.offer_name}`
    : null;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link to="/bills" className="text-sm text-[#1A7A4A]">
            ← Back to Bills
          </Link>
          <h1 className="mt-2 font-serif text-3xl font-bold text-[#1A1A18]">Bill #{bill.bill_number}</h1>
          <p className="mt-1 text-sm text-[#8A8A84]">
            {when.date}, {when.time}
          </p>
        </div>
        <a href={`/print/receipt/${bill.id}?from=bills`} target="_blank" rel="noreferrer">
          <Button>Print Receipt</Button>
        </a>
      </div>

      <div className="mb-4 grid gap-3 rounded-xl border border-[#E0DDD5] bg-white p-5 text-sm sm:grid-cols-2">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">Franchise</div>
          <div className="mt-1 font-medium">{bill.franchise_name ?? '—'}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">Cashier</div>
          <div className="mt-1 font-medium">{bill.cashier_name ?? '—'}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">Payment</div>
          <div className="mt-1 font-medium">{paymentLabel(bill.payment_method)}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">Status</div>
          <div className="mt-1">
            <Badge tone="green">{bill.payment_status || 'PAID'}</Badge>
          </div>
        </div>
        {bill.customer_phone ? (
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">Customer phone</div>
            <div className="mt-1 font-medium">{bill.customer_phone}</div>
          </div>
        ) : null}
        {bill.completed_at ? (
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">Completed</div>
            <div className="mt-1 font-medium">
              {when.date} {when.time}
            </div>
          </div>
        ) : null}
      </div>

      <div className="mb-4 overflow-hidden rounded-xl border border-[#E0DDD5] bg-white">
        <div className="border-b border-[#E0DDD5] px-5 py-3 text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
          Items
        </div>
        <div className="divide-y divide-[#E0DDD5]">
          {bill.items.map((item) => (
            <div
              key={item.id ?? `${item.product_id}-${item.quantity}-${item.line_total}`}
              className="flex items-start justify-between gap-4 px-5 py-3 text-sm"
            >
              <div>
                <div className="font-semibold">{item.product_name_snapshot}</div>
                <div className="text-[#8A8A84]">
                  {item.quantity} × {formatINR(item.unit_price)}
                </div>
              </div>
              <div className="font-semibold">{formatINR(item.line_total)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-[#E0DDD5] bg-white p-5 text-sm">
        <SummaryRow label="Subtotal" value={formatINR(bill.subtotal)} />
        {offerLabel ? <SummaryRow label={offerLabel} value={`−${formatINR(bill.discount_amount)}`} /> : (
          <SummaryRow
            label="Discount"
            value={bill.discount_amount > 0 ? `−${formatINR(bill.discount_amount)}` : formatINR(0)}
          />
        )}
        <SummaryRow label="Taxable" value={formatINR(bill.taxable_amount)} />
        <SummaryRow
          label={`CGST ${Number(bill.cgst_rate ?? 0).toFixed(1)}%`}
          value={formatINR(bill.cgst_amount ?? 0)}
        />
        <SummaryRow
          label={`SGST ${Number(bill.sgst_rate ?? 0).toFixed(1)}%`}
          value={formatINR(bill.sgst_amount ?? 0)}
        />
        <SummaryRow label="GST" value={formatINR(bill.gst_amount)} />
        <div className="mt-2 border-t border-[#E0DDD5] pt-2">
          <SummaryRow label="GRAND TOTAL" value={formatINR(bill.total_amount)} emphasize />
        </div>
      </div>
    </div>
  );
}
