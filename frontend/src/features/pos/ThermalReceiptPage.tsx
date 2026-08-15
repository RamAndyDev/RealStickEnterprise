import { useEffect, useRef } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorBanner, LoadingBlock } from '../../components/ui';
import { useAuth } from '../auth/AuthProvider';
import { fetchCompletedOrder } from '../../lib/ordersApi';
import { apiErrorMessage } from '../franchises/status';
import { formatINR } from '../../types/pos';
import './thermal-receipt.css';

function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatTime(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

function paymentLabel(method: string | null | undefined): string {
  if (!method) return '—';
  if (method === 'CASH') return 'Cash';
  if (method === 'UPI') return 'UPI';
  if (method === 'CARD') return 'Card';
  return method;
}

export function ThermalReceiptPage() {
  const { orderId } = useParams();
  const [params] = useSearchParams();
  const { profile } = useAuth();
  const autoprint = params.get('autoprint') === '1';
  const fromBills = params.get('from') === 'bills' || profile?.role !== 'EMPLOYEE';
  const printed = useRef(false);

  const orderQuery = useQuery({
    queryKey: ['completed-bill', orderId],
    queryFn: () => fetchCompletedOrder(orderId!),
    enabled: Boolean(orderId),
  });

  const order = orderQuery.data;

  useEffect(() => {
    if (!autoprint || !order || printed.current) return;
    printed.current = true;
    const timer = window.setTimeout(() => {
      window.print();
    }, 400);
    return () => window.clearTimeout(timer);
  }, [autoprint, order]);

  if (!orderId) {
    return <ErrorBanner message="Missing order id." />;
  }
  if (orderQuery.isLoading) {
    return <LoadingBlock label="Loading receipt…" />;
  }
  if (orderQuery.isError || !order) {
    return (
      <div className="p-6">
        <ErrorBanner message={apiErrorMessage(orderQuery.error, 'Unable to load receipt.')} />
        <Link to={fromBills ? '/bills' : '/pos'} className="mt-4 inline-block text-sm text-[#1A7A4A]">
          {fromBills ? 'Back to Bills' : 'Back to POS'}
        </Link>
      </div>
    );
  }

  const when = order.completed_at || order.created_at;
  const address = [order.franchise_address, order.franchise_city, order.franchise_state]
    .filter(Boolean)
    .join(', ');

  return (
    <div className="thermal-receipt-page min-h-screen bg-[#FDFAF4]">
      <div className="thermal-receipt-actions no-print mx-auto flex max-w-[420px] items-center justify-between gap-3 px-4 py-4">
        <Link to={fromBills ? '/bills' : '/pos'} className="text-sm text-[#1A7A4A]">
          {fromBills ? '← Back to Bills' : '← Back to POS'}
        </Link>
        <Button size="sm" onClick={() => window.print()}>
          Print again
        </Button>
      </div>

      <div className="thermal-receipt mx-auto">
        <div className="center">
          <div className="brand">RealStick™</div>
          <div>Natural Popsicles & Kulfi</div>
          <div>{order.franchise_name || 'Outlet'}</div>
          {address ? <div>{address}</div> : null}
          <div>realstick.in</div>
        </div>
        <hr />
        <div>Bill No: {order.bill_number}</div>
        <div>Date: {formatDate(when)}</div>
        <div>Time: {formatTime(when)}</div>
        <div>Staff: {order.cashier_name || '—'}</div>
        <hr />
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th className="qty">Qty</th>
              <th className="num">Price</th>
              <th className="num">Amt</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((item) => (
              <tr key={`${item.product_id}-${item.quantity}-${item.line_total}`}>
                <td>{item.product_name_snapshot}</td>
                <td className="qty">×{item.quantity}</td>
                <td className="num">{formatINR(item.unit_price)}</td>
                <td className="num">{formatINR(item.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <hr />
        <table>
          <tbody>
            <tr>
              <td>Subtotal</td>
              <td className="num">{formatINR(order.subtotal)}</td>
            </tr>
            {order.offer_name ? (
              <tr>
                <td colSpan={2}>Offer: {order.offer_name}</td>
              </tr>
            ) : null}
            <tr>
              <td>
                {order.offer_name && order.discount_value != null
                  ? `Discount ${Number(order.discount_value).toFixed(0)}%`
                  : 'Discount'}
              </td>
              <td className="num">
                {order.discount_amount > 0
                  ? `−${formatINR(order.discount_amount)}`
                  : formatINR(0)}
              </td>
            </tr>
          </tbody>
        </table>
        <hr />
        <table>
          <tbody>
            <tr>
              <td>Taxable Amount</td>
              <td className="num">{formatINR(order.taxable_amount)}</td>
            </tr>
            <tr>
              <td>CGST @ {Number(order.cgst_rate ?? 0).toFixed(2)}%</td>
              <td className="num">{formatINR(order.cgst_amount ?? 0)}</td>
            </tr>
            <tr>
              <td>SGST @ {Number(order.sgst_rate ?? 0).toFixed(2)}%</td>
              <td className="num">{formatINR(order.sgst_amount ?? 0)}</td>
            </tr>
          </tbody>
        </table>
        <hr />
        <table>
          <tbody>
            <tr>
              <td>Total GST</td>
              <td className="num">{formatINR(order.gst_amount)}</td>
            </tr>
            <tr className="total">
              <td>GRAND TOTAL</td>
              <td className="num">{formatINR(order.total_amount)}</td>
            </tr>
            <tr>
              <td>Payment</td>
              <td className="num">{paymentLabel(order.payment_method)}</td>
            </tr>
            <tr>
              <td>Payment Status</td>
              <td className="num">{order.payment_status || 'PAID'}</td>
            </tr>
          </tbody>
        </table>
        <hr />
        <div className="center footer">
          <div>Real Fruits. Real Goodness.</div>
          <div>Zero Artificial · Zero Preservatives</div>
          <div>Thank you! Visit again 🍡</div>
        </div>
      </div>
    </div>
  );
}
