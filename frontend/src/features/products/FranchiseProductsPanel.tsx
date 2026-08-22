import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import {
  ActionButton,
  ActionGroup,
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  LoadingBlock,
  Modal,
  SuccessBanner,
} from '../../components/ui';
import {
  listFranchiseProducts,
  listProducts,
  updateFranchiseProduct,
} from '../../lib/productsApi';
import {
  formatINR,
  sellingPriceError,
  type FranchiseProductAssignment,
  type Product,
} from '../../types/product';
import { apiErrorMessage } from '../franchises/status';
import { AssignProductsDialog } from './AssignProductsDialog';
import { assignmentUpdateSuccessMessage } from './assignmentUpdate';
import { categoryColor } from './categoryColors';
import { ProductImage } from './ProductImage';

const EMPTY_PRODUCTS: Product[] = [];

export function FranchiseProductsPanel({
  franchiseId,
  franchiseName,
}: {
  franchiseId: string;
  franchiseName?: string;
}) {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAssign, setShowAssign] = useState(false);
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
    onSuccess: async (_data, variables) => {
      setEditRow(null);
      setFeedback(assignmentUpdateSuccessMessage(variables));
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
        <Button size="sm" onClick={() => setShowAssign(true)}>
          Assign products
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
                  Master {formatINR(item.master_price)} · Reference only
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
              <ActionGroup>
                <ActionButton
                  variant="outline"
                  onClick={() => {
                    setEditRow(item);
                    setEditPrice(String(item.selling_price));
                  }}
                >
                  Edit
                </ActionButton>
                <ActionButton
                  fit="xl"
                  variant={item.is_active ? 'outline' : 'muted'}
                  onClick={() =>
                    updateMutation.mutate({
                      product_id: item.product_id,
                      is_active: !item.is_active,
                    })
                  }
                >
                  {item.is_active ? 'Assignment Active' : 'Assignment Hidden'}
                </ActionButton>
              </ActionGroup>
            </div>
          ))}
        </div>
      )}

      {showAssign ? (
        <AssignProductsDialog
          franchiseId={franchiseId}
          franchiseName={franchiseName}
          products={productsQuery.data?.items ?? EMPTY_PRODUCTS}
          assignments={items}
          loading={productsQuery.isLoading}
          loadError={
            productsQuery.isError
              ? apiErrorMessage(productsQuery.error, 'Unable to load products.')
              : null
          }
          onClose={() => setShowAssign(false)}
          onSaved={async () => {
            setShowAssign(false);
            setFeedback('Product assignments saved.');
            setError(null);
            await queryClient.invalidateQueries({
              queryKey: ['admin-franchise-products', franchiseId],
            });
          }}
        />
      ) : null}

      {editRow ? (
        <Modal title="Edit selling price" onClose={() => setEditRow(null)}>
          <p className="mb-1 text-sm font-medium text-[#1A1A18]">{editRow.product_name}</p>
          <p className="mb-0.5 text-sm text-[#5C5C56]">
            Master Price {formatINR(editRow.master_price)}
          </p>
          <p className="mb-3 text-[11px] text-[#8A8A84]">Master Price is for reference only.</p>
          <Field
            label="Franchise Selling Price (₹)"
            type="number"
            min={0.01}
            step="0.01"
            value={editPrice}
            error={sellingPriceError(editPrice) ?? undefined}
            onChange={(e) => setEditPrice(e.target.value)}
          />
          <p className="mb-3 text-[11px] text-[#8A8A84]">
            Set the selling price for this franchise.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={() => setEditRow(null)}>
              Cancel
            </Button>
            <Button
              disabled={
                Boolean(sellingPriceError(editPrice)) ||
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
