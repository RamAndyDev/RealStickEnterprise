import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { ErrorBanner, LoadingBlock } from '../../components/ui';
import { validatePhone } from '../../lib/validation';
import { fetchPosMenu, fetchPosOffers, completePosOrder } from '../../lib/posApi';
import { categoryColor } from '../products/categoryColors';
import { ProductImage } from '../products/ProductImage';
import { useAuth } from '../auth/AuthProvider';
import { apiErrorMessage } from '../franchises/status';
import type { PosCartLine, PosMenuItem, PosPaymentMethod } from '../../types/pos';
import { formatINR, previewTotals } from '../../types/pos';
import { CartPanel } from './CartPanel';
import { CheckoutModal } from './CheckoutModal';

const MAX_QTY = 999;

export function PosPage() {
  const { profile } = useAuth();
  const navigate = useNavigate();

  const [category, setCategory] = useState('All');
  const [search, setSearch] = useState('');
  const [cart, setCart] = useState<PosCartLine[]>([]);
  const [paymentMethod, setPaymentMethod] = useState<PosPaymentMethod>('UPI');
  const [phone, setPhone] = useState('');
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);

  const menuQuery = useQuery({
    queryKey: ['pos-menu'],
    queryFn: fetchPosMenu,
  });

  const offersQuery = useQuery({
    queryKey: ['pos-offers'],
    queryFn: fetchPosOffers,
  });

  const checkoutMutation = useMutation({
    mutationFn: completePosOrder,
    onSuccess: (order) => {
      setCart([]);
      setSelectedOfferId(null);
      setPhone('');
      setConfirmOpen(false);
      setSuccess('Bill saved & printing…');
      navigate(`/print/receipt/${order.id}?autoprint=1`);
    },
    onError: (err) => {
      setCheckoutError(apiErrorMessage(err, 'Unable to complete order.'));
    },
  });

  const menu = menuQuery.data;
  const gstRate = menu?.gst_rate ?? null;
  const items = menu?.items ?? [];
  const offers = offersQuery.data?.items ?? [];
  const selectedOffer = offers.find((offer) => offer.id === selectedOfferId) ?? null;

  useEffect(() => {
    if (selectedOfferId && !offers.some((offer) => offer.id === selectedOfferId)) {
      setSelectedOfferId(null);
    }
  }, [offers, selectedOfferId]);

  const chips = useMemo(() => {
    const names = (menu?.categories ?? []).map((row) => row.name);
    return ['All', ...names];
  }, [menu?.categories]);

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
            return items.filter((item) => {
      if (!item.available_for_pos) return false;
      if (category !== 'All' && item.category_name !== category) return false;
      if (needle && !item.name.toLowerCase().includes(needle)) return false;
      return true;
    });
  }, [items, category, search]);

  function addItem(item: PosMenuItem) {
    if (!item.available_for_pos) return;
    setCart((prev) => {
      const existing = prev.find((line) => line.product_id === item.product_id);
      if (existing) {
        return prev.map((line) =>
          line.product_id === item.product_id
            ? { ...line, quantity: Math.min(MAX_QTY, line.quantity + 1) }
            : line,
        );
      }
      return [
        ...prev,
        {
          product_id: item.product_id,
          name: item.name,
          image_url: item.image_url,
          selling_price: item.selling_price,
          quantity: 1,
        },
      ];
    });
  }

  function changeQty(productId: string, delta: number) {
    setCart((prev) =>
      prev
        .map((line) =>
          line.product_id === productId
            ? { ...line, quantity: Math.max(0, Math.min(MAX_QTY, line.quantity + delta)) }
            : line,
        )
        .filter((line) => line.quantity > 0),
    );
  }

  const totals = previewTotals(cart, selectedOffer?.discount_value ?? 0, gstRate);

  function confirmCheckout() {
    setCheckoutError(null);
    const phoneError = validatePhone(phone, false);
    if (phoneError) {
      setCheckoutError(phoneError);
      return;
    }
    checkoutMutation.mutate({
      items: cart.map((line) => ({ product_id: line.product_id, quantity: line.quantity })),
      payment_method: paymentMethod,
      customer_phone: phone.trim() || null,
      offer_id: selectedOfferId,
    });
  }

  if (menuQuery.isLoading) {
    return <LoadingBlock label="Loading POS menu…" />;
  }

  if (menuQuery.isError) {
    return (
      <ErrorBanner message={apiErrorMessage(menuQuery.error, 'Unable to load POS menu.')} />
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden md:flex-row">
      <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-[#FDFAF4]">
        <div className="border-b border-[#E0DDD5] bg-white px-3 py-2.5">
          <input
            placeholder="🔍 Search menu..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="mb-2 w-full rounded-lg border border-[#E0DDD5] px-2.5 py-2.5 text-base outline-none focus:border-[#1A7A4A] md:py-2 md:text-[13px]"
          />
          <div className="flex flex-wrap gap-1.5">
            {chips.map((chip) => {
              const selected = category === chip;
              const color = chip === 'All' ? '#8A8A84' : categoryColor(chip);
              return (
                <button
                  key={chip}
                  type="button"
                  onClick={() => {
                    setCategory(chip);
                    setSearch('');
                  }}
                  className="min-h-11 rounded-full px-3 text-[13px] font-semibold md:min-h-0 md:px-2.5 md:py-1 md:text-[11px]"
                  style={{
                    background: selected ? color : 'transparent',
                    color: selected ? '#fff' : '#4A4A46',
                    border: selected ? 'none' : '1px solid #E0DDD5',
                  }}
                >
                  {chip}
                </button>
              );
            })}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-2.5">
          {!items.length ? (
            <div className="px-4 py-10 text-center text-[13px] text-[#8A8A84]">
              No products assigned to this franchise.
            </div>
          ) : null}
          {items.length && !visible.length ? (
            <div className="px-4 py-10 text-center text-[13px] text-[#8A8A84]">No items found</div>
          ) : null}
          <div className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] content-start gap-2 md:grid-cols-[repeat(auto-fill,minmax(135px,1fr))]">
            {visible.map((item) => {
              const color = categoryColor(item.category_name);
              const available = item.available_for_pos;
              return (
                <button
                  key={item.product_id}
                  type="button"
                  disabled={!available}
                  onClick={() => addItem(item)}
                  className="min-h-[44px] rounded-[10px] border border-[#E0DDD5] bg-white px-2.5 py-2.5 text-left"
                  style={{
                    borderTop: `3px solid ${color}`,
                    opacity: available ? 1 : 0.5,
                    cursor: available ? 'pointer' : 'not-allowed',
                  }}
                >
                  <div className="mb-1.5 flex h-10 items-center justify-center">
                    <ProductImage
                      src={item.image_url}
                      alt={item.name}
                      size="sm"
                      className="h-10 w-10"
                    />
                  </div>
                  <div className="mb-0.5 text-[12px] font-semibold leading-tight text-[#1A1A18]">
                    {item.name}
                  </div>
                  <div className="mb-1.5 text-[9px] leading-snug text-[#8A8A84]">
                    {item.category_name}
                    {item.description ? ` · ${item.description}` : ''}
                  </div>
                  <div
                    className="font-serif text-[14px] font-bold"
                    style={{ color: available ? color : '#8A8A84' }}
                  >
                    {formatINR(item.selling_price)}
                  </div>
                  {!available ? (
                    <div className="mt-1 text-[9px] font-semibold uppercase tracking-wide text-[#8A8A84]">
                      Unavailable
                    </div>
                  ) : null}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      <CartPanel
        cashierName={profile?.full_name || 'Staff'}
        franchiseName={menu?.franchise_name || profile?.franchise_name || 'Outlet'}
        lines={cart}
        gstRate={gstRate}
        offers={offers}
        selectedOfferId={selectedOfferId}
        paymentMethod={paymentMethod}
        phone={phone}
        success={success}
        onIncrease={(id) => changeQty(id, 1)}
        onDecrease={(id) => changeQty(id, -1)}
        onRemove={(id) => setCart((prev) => prev.filter((line) => line.product_id !== id))}
        onClear={() => setCart([])}
        onSelectOffer={setSelectedOfferId}
        onPaymentMethod={setPaymentMethod}
        onPhone={setPhone}
        onCheckout={() => {
          setCheckoutError(null);
          setConfirmOpen(true);
        }}
      />

      {confirmOpen ? (
        <CheckoutModal
          total={totals.total}
          paymentMethod={paymentMethod}
          submitting={checkoutMutation.isPending}
          error={checkoutError}
          onConfirm={confirmCheckout}
          onClose={() => {
            if (!checkoutMutation.isPending) setConfirmOpen(false);
          }}
        />
      ) : null}
    </div>
  );
}
