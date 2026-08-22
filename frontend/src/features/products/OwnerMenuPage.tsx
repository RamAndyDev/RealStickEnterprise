import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import {
  ActionButton,
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  LoadingBlock,
  Modal,
  SuccessBanner,
} from '../../components/ui';
import { listOwnerMenu, updateOwnerMenuItem } from '../../lib/productsApi';
import {
  formatINR,
  ownerCanEditSellingPrice,
  sellingPriceError,
  type FranchiseProductAssignment,
} from '../../types/product';
import { useAuth } from '../auth/AuthProvider';
import { apiErrorMessage } from '../franchises/status';
import { categoryColor } from './categoryColors';
import { ProductImage } from './ProductImage';

export function OwnerMenuPage() {
  const { profile } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');
  const [editRow, setEditRow] = useState<FranchiseProductAssignment | null>(null);
  const [editPrice, setEditPrice] = useState('');
  const [priceTouched, setPriceTouched] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const menuQuery = useQuery({
    queryKey: ['owner-menu'],
    queryFn: listOwnerMenu,
  });

  const updateMutation = useMutation({
    mutationFn: ({
      product_id,
      selling_price,
    }: {
      product_id: string;
      selling_price: number;
    }) => updateOwnerMenuItem(product_id, { selling_price }),
    onSuccess: async () => {
      setEditRow(null);
      setFeedback('Franchise selling price updated.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['owner-menu'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update menu item.')),
  });

  const items = menuQuery.data?.items ?? [];
  const franchiseLabel =
    profile?.franchise_name ||
    (profile?.franchise_id ? `Franchise ${profile.franchise_id}` : 'Your franchise');

  const categories = useMemo(() => {
    const names = new Set<string>();
    for (const item of items) {
      if (item.category_name) names.add(item.category_name);
    }
    return [...names].sort((a, b) => a.localeCompare(b));
  }, [items]);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return items.filter((item) => {
      if (activeCategory !== 'All' && item.category_name !== activeCategory) return false;
      if (!needle) return true;
      return (
        (item.product_name ?? '').toLowerCase().includes(needle) ||
        (item.category_name ?? '').toLowerCase().includes(needle) ||
        (item.product_description ?? '').toLowerCase().includes(needle)
      );
    });
  }, [items, search, activeCategory]);

  const grouped = useMemo(() => {
    const groups = new Map<string, FranchiseProductAssignment[]>();
    for (const item of filtered) {
      const key = item.category_name ?? 'Uncategorized';
      const list = groups.get(key) ?? [];
      list.push(item);
      groups.set(key, list);
    }
    return [...groups.entries()];
  }, [filtered]);

  const availableCount = items.filter((item) => item.available_for_pos).length;
  const editPriceError = sellingPriceError(editPrice);

  if (menuQuery.isLoading) {
    return <LoadingBlock label="Loading franchise menu…" />;
  }

  if (menuQuery.isError) {
    return (
      <ErrorBanner message={apiErrorMessage(menuQuery.error, 'Unable to load franchise menu.')} />
    );
  }

  const chips = ['All', ...categories];

  return (
    <div className="mx-auto max-w-[840px]">
      <div className="mb-4">
        <h1 className="font-serif text-[20px] font-bold text-[#1A1A18]">Menu / Pricing</h1>
        <p className="text-xs text-[#8A8A84]">
          {franchiseLabel} · {availableCount} available · {items.length - availableCount} unavailable
        </p>
      </div>

      {feedback ? (
        <div className="mb-3">
          <SuccessBanner message={feedback} />
        </div>
      ) : null}
      {error ? (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      ) : null}

      <div className="mb-4 rounded-[10px] border border-[#E0DDD5] bg-white p-3">
        <input
          placeholder="🔍 Search menu..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="mb-2 w-full rounded-lg border border-[#E0DDD5] px-3 py-2 text-[13px] outline-none focus:border-[#1A7A4A]"
        />
        <div className="flex flex-wrap gap-1.5">
          {chips.map((chip) => {
            const selected = activeCategory === chip;
            const color = chip === 'All' ? '#8A8A84' : categoryColor(chip);
            return (
              <button
                key={chip}
                type="button"
                onClick={() => setActiveCategory(chip)}
                className="rounded-full px-2.5 py-1 text-[11px] font-semibold"
                style={{
                  background: selected ? color : 'transparent',
                  color: selected ? '#fff' : '#5C5C56',
                  border: selected ? 'none' : '1px solid #E0DDD5',
                }}
              >
                {chip}
              </button>
            );
          })}
        </div>
      </div>

      {!items.length ? (
        <EmptyState
          title="No products assigned"
          hint="Your System Admin assigns products and sets the initial franchise selling price."
        />
      ) : null}

      {items.length && !filtered.length ? (
        <EmptyState title="No items found" hint="Try a different search or category." />
      ) : null}

      {grouped.map(([categoryName, categoryItems]) => (
        <div key={categoryName} className="mb-5">
          <div
            className="mb-2 text-[10px] font-semibold uppercase tracking-[.08em]"
            style={{ color: categoryColor(categoryName) }}
          >
            {categoryName} ({categoryItems.length})
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {categoryItems.map((item) => {
              const canEditPrice = ownerCanEditSellingPrice(item);
              return (
                <article
                  key={item.id}
                  className="overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white"
                  style={{ opacity: canEditPrice ? 1 : 0.72 }}
                >
                  <div className="flex h-36 items-center justify-center bg-[#F3F1EB]">
                    {item.image_url ? (
                      <img
                        src={item.image_url}
                        alt={item.product_name ?? 'Product'}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <ProductImage
                        src={item.image_url}
                        alt={item.product_name ?? 'Product'}
                        size="lg"
                      />
                    )}
                  </div>
                  <div className="p-3.5">
                    <h2 className="font-serif text-base font-bold text-[#1A1A18]">
                      {item.product_name ?? 'Untitled product'}
                    </h2>
                    <div
                      className="text-[10px] font-semibold uppercase tracking-[.06em]"
                      style={{ color: categoryColor(item.category_name) }}
                    >
                      {item.category_name ?? 'Uncategorized'}
                    </div>
                    <div className="mt-1.5 text-[11px] text-[#8A8A84]">
                      Master {formatINR(item.master_price)} · Reference only
                    </div>
                    <div className="mt-1 text-[10px] uppercase tracking-[.05em] text-[#8A8A84]">
                      Your Selling Price
                    </div>
                    <div className="mt-0.5 font-serif text-xl font-bold text-[#1A7A4A]">
                      {formatINR(item.selling_price)}
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {canEditPrice ? (
                        <Badge tone={item.available_for_pos ? 'green' : 'muted'}>
                          {item.available_for_pos ? 'Available' : 'Unavailable'}
                        </Badge>
                      ) : (
                        <Badge tone="muted">Inactive</Badge>
                      )}
                    </div>
                    <div className="mt-3">
                      <ActionButton
                        fit="lg"
                        variant="outline"
                        disabled={!canEditPrice}
                        onClick={() => {
                          if (!canEditPrice) return;
                          setEditRow(item);
                          setEditPrice(String(item.selling_price));
                          setPriceTouched(false);
                        }}
                      >
                        Edit Price
                      </ActionButton>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      ))}

      {editRow ? (
        <Modal title="Edit Price" onClose={() => setEditRow(null)}>
          <div className="mb-3">
            <div className="font-serif text-base font-bold text-[#1A1A18]">
              {editRow.product_name}
            </div>
            <div className="text-xs text-[#8A8A84]">
              Current franchise price {formatINR(editRow.selling_price)} · Master{' '}
              {formatINR(editRow.master_price)}
            </div>
            <p className="mt-1 text-[11px] text-[#8A8A84]">
              Master Price is for reference only.
            </p>
          </div>
          <Field
            label="Your Selling Price (₹)"
            type="number"
            min={0.01}
            step="0.01"
            value={editPrice}
            error={priceTouched ? editPriceError ?? undefined : undefined}
            onChange={(e) => {
              setEditPrice(e.target.value);
              setPriceTouched(true);
            }}
          />
          <p className="mb-3 text-[11px] text-[#8A8A84]">
            Set the selling price for this franchise.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={() => setEditRow(null)}>
              Cancel
            </Button>
            <Button
              disabled={Boolean(editPriceError) || updateMutation.isPending}
              onClick={() => {
                setPriceTouched(true);
                if (editPriceError) return;
                updateMutation.mutate({
                  product_id: editRow.product_id,
                  selling_price: Number(editPrice),
                });
              }}
            >
              {updateMutation.isPending ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
