import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  LoadingBlock,
  Modal,
  SelectField,
  SuccessBanner,
} from '../../components/ui';
import {
  assignFranchiseProduct,
  listFranchiseProducts,
  listProducts,
  updateFranchiseProduct,
} from '../../lib/productsApi';
import {
  formatINR,
  sellingPriceError,
  type FranchiseProductAssignment,
} from '../../types/product';
import { apiErrorMessage } from '../franchises/status';
import { categoryColor } from './categoryColors';
import { ProductImage } from './ProductImage';

export function FranchiseProductsPanel({ franchiseId }: { franchiseId: string }) {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAssign, setShowAssign] = useState(false);
  const [productId, setProductId] = useState('');
  const [sellingPrice, setSellingPrice] = useState('');
  const [editRow, setEditRow] = useState<FranchiseProductAssignment | null>(null);
  const [editPrice, setEditPrice] = useState('');

  const assignmentsQuery = useQuery({
    queryKey: ['admin-franchise-products', franchiseId],
    queryFn: () => listFranchiseProducts(franchiseId),
  });

  const productsQuery = useQuery({
    queryKey: ['admin-products'],
    queryFn: () => listProducts({}),
  });

  const assignedIds = useMemo(
    () => new Set((assignmentsQuery.data?.items ?? []).map((a) => a.product_id)),
    [assignmentsQuery.data],
  );

  const unassignedProducts = (productsQuery.data?.items ?? []).filter(
    (p) => !assignedIds.has(p.id),
  );
  const selectedMaster = unassignedProducts.find((p) => p.id === productId)?.price;

  const assignMutation = useMutation({
    mutationFn: () =>
      assignFranchiseProduct(franchiseId, {
        product_id: productId,
        selling_price: Number(sellingPrice),
        is_active: true,
      }),
    onSuccess: async () => {
      setShowAssign(false);
      setProductId('');
      setSellingPrice('');
      setFeedback('Product assigned.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-franchise-products', franchiseId] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to assign product.')),
  });

  const updateMutation = useMutation({
    mutationFn: ({
      product_id,
      selling_price,
      is_active,
    }: {
      product_id: string;
      selling_price?: number;
      is_active?: boolean;
    }) => updateFranchiseProduct(franchiseId, product_id, { selling_price, is_active }),
    onSuccess: async () => {
      setEditRow(null);
      setFeedback('Franchise pricing updated.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-franchise-products', franchiseId] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update pricing.')),
  });

  const items = assignmentsQuery.data?.items ?? [];

  if (assignmentsQuery.isLoading) {
    return <LoadingBlock label="Loading franchise menu…" />;
  }

  if (assignmentsQuery.isError) {
    return (
      <ErrorBanner
        message={apiErrorMessage(assignmentsQuery.error, 'Unable to load franchise products.')}
      />
    );
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-serif text-lg font-bold text-[#1A1A18]">Menu & pricing</h2>
          <p className="text-xs text-[#8A8A84]">
            {items.length} assigned · selling price is franchise-specific
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => setShowAssign(true)}
          disabled={!unassignedProducts.length}
        >
          + Assign product
        </Button>
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

      {!items.length ? (
        <EmptyState
          title="No products assigned"
          hint="Assign catalog items and set franchise selling prices."
        />
      ) : (
        <div className="overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white">
          {items.map((item, idx) => (
            <div
              key={item.id}
              className="flex flex-wrap items-center gap-3 px-4 py-3"
              style={{
                borderBottom: idx < items.length - 1 ? '1px solid #E0DDD5' : undefined,
                opacity: item.is_active && item.product_is_active ? 1 : 0.5,
              }}
            >
              <ProductImage src={item.image_url} alt={item.product_name ?? 'Product'} size="sm" />
              <div className="min-w-0 flex-1">
                <Link
                  to={`/products/${item.product_id}`}
                  className="text-sm font-medium text-[#1A1A18] hover:text-[#1A7A4A]"
                >
                  {item.product_name}
                </Link>
                <div
                  className="text-[10px] font-semibold uppercase tracking-[.06em]"
                  style={{ color: categoryColor(item.category_name) }}
                >
                  {item.category_name ?? '—'}
                </div>
                <div className="text-[11px] text-[#8A8A84]">
                  Master {formatINR(item.master_price)}
                  {!item.product_is_active ? ' · globally Hidden' : ''}
                  {!item.available_for_pos ? ' · not available for POS' : ''}
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] uppercase tracking-[.05em] text-[#8A8A84]">
                  Selling price
                </div>
                <div className="font-serif text-base font-bold text-[#1A7A4A]">
                  {formatINR(item.selling_price)}
                </div>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setEditRow(item);
                  setEditPrice(String(item.selling_price));
                }}
              >
                Edit
              </Button>
              <button
                type="button"
                onClick={() =>
                  updateMutation.mutate({
                    product_id: item.product_id,
                    is_active: !item.is_active,
                  })
                }
                className="rounded-md border border-[#E0DDD5] px-2.5 py-1 text-[11px] font-semibold"
                style={{
                  background: item.is_active ? '#E6F4EC' : '#FDFAF4',
                  color: item.is_active ? '#1A7A4A' : '#8A8A84',
                }}
              >
                {item.is_active ? 'Active' : 'Hidden'}
              </button>
            </div>
          ))}
        </div>
      )}

      {showAssign ? (
        <Modal title="Assign product" onClose={() => setShowAssign(false)}>
          <SelectField
            label="Product"
            value={productId}
            onChange={(e) => {
              const id = e.target.value;
              setProductId(id);
              const product = unassignedProducts.find((p) => p.id === id);
              if (product) setSellingPrice('');
            }}
          >
            <option value="">Select product</option>
            {unassignedProducts.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} · master {formatINR(p.price)}
              </option>
            ))}
          </SelectField>
          <Field
            label="Franchise Selling Price (₹)"
            type="number"
            min={0.01}
            step="0.01"
            value={sellingPrice}
            error={sellingPrice ? sellingPriceError(sellingPrice, selectedMaster) ?? undefined : undefined}
            onChange={(e) => setSellingPrice(e.target.value)}
          />
          <p className="mb-3 text-[11px] text-[#8A8A84]">
            Must be greater than 0 and strictly less than the master price
            {selectedMaster != null ? ` (${formatINR(selectedMaster)})` : ''}.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={() => setShowAssign(false)}>
              Cancel
            </Button>
            <Button
              disabled={
                !productId ||
                Boolean(sellingPriceError(sellingPrice, selectedMaster)) ||
                assignMutation.isPending
              }
              onClick={() => assignMutation.mutate()}
            >
              {assignMutation.isPending ? 'Saving…' : 'Assign'}
            </Button>
          </div>
        </Modal>
      ) : null}

      {editRow ? (
        <Modal title="Edit selling price" onClose={() => setEditRow(null)}>
          <p className="mb-3 text-sm text-[#5C5C56]">
            {editRow.product_name} · Master {formatINR(editRow.master_price)}
          </p>
          <Field
            label="Franchise Selling Price (₹)"
            type="number"
            min={0.01}
            step="0.01"
            value={editPrice}
            error={sellingPriceError(editPrice, editRow.master_price) ?? undefined}
            onChange={(e) => setEditPrice(e.target.value)}
          />
          <p className="mb-3 text-[11px] text-[#8A8A84]">
            Must be greater than 0 and strictly less than the master price.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={() => setEditRow(null)}>
              Cancel
            </Button>
            <Button
              disabled={
                Boolean(sellingPriceError(editPrice, editRow.master_price)) ||
                updateMutation.isPending
              }
              onClick={() =>
                updateMutation.mutate({
                  product_id: editRow.product_id,
                  selling_price: Number(editPrice),
                })
              }
            >
              {updateMutation.isPending ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
