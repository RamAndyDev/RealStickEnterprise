import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import {
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  LoadingBlock,
  Modal,
  SelectField,
  SuccessBanner,
} from '../../components/ui';
import { listFranchises } from '../../lib/franchisesApi';
import {
  assignFranchiseProduct,
  getProduct,
  listFranchiseProducts,
  updateFranchiseProduct,
  updateProduct,
} from '../../lib/productsApi';
import {
  formatINR,
  sellingPriceError,
  type FranchiseProductAssignment,
} from '../../types/product';
import { apiErrorMessage } from '../franchises/status';
import { categoryColor } from './categoryColors';
import { ProductImage } from './ProductImage';

type FranchiseAssignmentRow = FranchiseProductAssignment & {
  franchise_name?: string;
};

export function ProductDetailPage() {
  const { productId } = useParams<{ productId: string }>();
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAssign, setShowAssign] = useState(false);
  const [franchiseId, setFranchiseId] = useState('');
  const [sellingPrice, setSellingPrice] = useState('');
  const [assignActive, setAssignActive] = useState(true);
  const [editAssignment, setEditAssignment] = useState<FranchiseAssignmentRow | null>(null);
  const [editPrice, setEditPrice] = useState('');

  const productQuery = useQuery({
    queryKey: ['admin-product', productId],
    queryFn: () => getProduct(productId!),
    enabled: Boolean(productId),
  });

  const franchisesQuery = useQuery({
    queryKey: ['admin-franchises-for-products'],
    queryFn: () => listFranchises({}),
  });

  const franchises = franchisesQuery.data?.items ?? [];

  const assignmentQueries = useQuery({
    queryKey: ['admin-product-assignments', productId, franchises.map((f) => f.id).join(',')],
    queryFn: async () => {
      const rows: FranchiseAssignmentRow[] = [];
      for (const franchise of franchises) {
        const result = await listFranchiseProducts(franchise.id);
        for (const item of result.items) {
          if (item.product_id === productId) {
            rows.push({ ...item, franchise_name: franchise.name });
          }
        }
      }
      return rows;
    },
    enabled: Boolean(productId) && franchises.length > 0,
  });

  const assignedIds = useMemo(
    () => new Set((assignmentQueries.data ?? []).map((a) => a.franchise_id)),
    [assignmentQueries.data],
  );

  const unassignedFranchises = franchises.filter((f) => !assignedIds.has(f.id));

  const toggleProductMutation = useMutation({
    mutationFn: (is_active: boolean) => updateProduct(productId!, { is_active }),
    onSuccess: async (data) => {
      setFeedback(data.is_active ? 'Item set to Active.' : 'Item set to Hidden.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-product', productId] });
      await queryClient.invalidateQueries({ queryKey: ['admin-products'] });
      await queryClient.invalidateQueries({ queryKey: ['admin-product-assignments', productId] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update item.')),
  });

  const assignMutation = useMutation({
    mutationFn: () =>
      assignFranchiseProduct(franchiseId, {
        product_id: productId!,
        selling_price: Number(sellingPrice),
        is_active: assignActive,
      }),
    onSuccess: async () => {
      setShowAssign(false);
      setFranchiseId('');
      setSellingPrice('');
      setAssignActive(true);
      setFeedback('Product assigned to franchise.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-product-assignments', productId] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to assign product.')),
  });

  const updateAssignmentMutation = useMutation({
    mutationFn: ({
      franchise_id,
      selling_price,
      is_active,
    }: {
      franchise_id: string;
      selling_price?: number;
      is_active?: boolean;
    }) => updateFranchiseProduct(franchise_id, productId!, { selling_price, is_active }),
    onSuccess: async () => {
      setEditAssignment(null);
      setFeedback('Franchise pricing updated.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-product-assignments', productId] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update franchise pricing.')),
  });

  if (!productId) {
    return <ErrorBanner message="Missing product id." />;
  }

  if (productQuery.isLoading) {
    return <LoadingBlock label="Loading item…" />;
  }

  if (productQuery.isError || !productQuery.data) {
    return (
      <ErrorBanner message={apiErrorMessage(productQuery.error, 'Unable to load item.')} />
    );
  }

  const product = productQuery.data;
  const catColor = categoryColor(product.category?.name);
  const assignments = assignmentQueries.data ?? [];

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4">
        <Link to="/products" className="text-sm text-[#1A7A4A] hover:underline">
          ← Menu Management
        </Link>
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

      <div className="mb-4 overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white">
        <div className="h-1" style={{ background: catColor }} />
        <div className="flex flex-wrap items-start gap-4 p-5">
          <ProductImage product={product} size="lg" />
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">{product.name}</h1>
              <Badge tone={product.is_active ? 'green' : 'muted'}>
                {product.is_active ? 'Active' : 'Hidden'}
              </Badge>
            </div>
            <p className="text-sm text-[#8A8A84]">{product.description || 'No description'}</p>
            <p className="mt-2 text-xs font-semibold uppercase tracking-[.06em]" style={{ color: catColor }}>
              {product.category?.name ?? 'Uncategorized'}
            </p>
          </div>
          <div className="text-right">
            <div className="text-[10px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
              Master price
            </div>
            <div className="font-serif text-2xl font-bold text-[#1A7A4A]">
              {formatINR(product.price)}
            </div>
            <Button
              size="sm"
              variant="outline"
              className="mt-2"
              onClick={() => toggleProductMutation.mutate(!product.is_active)}
            >
              {product.is_active ? 'Set Hidden' : 'Set Active'}
            </Button>
          </div>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-serif text-lg font-bold text-[#1A1A18]">Franchise pricing</h2>
          <p className="text-xs text-[#8A8A84]">
            Selling price is what POS will use. Assignment Active/Hidden controls franchise availability.
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => {
            setSellingPrice(String(product.price));
            setShowAssign(true);
          }}
          disabled={!unassignedFranchises.length}
        >
          + Assign to franchise
        </Button>
      </div>

      {assignmentQueries.isLoading ? (
        <LoadingBlock label="Loading franchise assignments…" />
      ) : !assignments.length ? (
        <EmptyState
          title="Not assigned to any franchise"
          hint="Assign this item and set a franchise selling price."
        />
      ) : (
        <div className="overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white">
          {assignments.map((row, idx) => (
            <div
              key={row.id}
              className="flex flex-wrap items-center gap-3 px-4 py-3"
              style={{
                borderBottom: idx < assignments.length - 1 ? '1px solid #E0DDD5' : undefined,
                opacity: row.is_active ? 1 : 0.55,
              }}
            >
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium text-[#1A1A18]">
                  {row.franchise_name ?? row.franchise_id}
                </div>
                <div className="text-[11px] text-[#8A8A84]">
                  Master {formatINR(row.master_price)} ·{' '}
                  {row.available_for_pos ? 'Available for POS' : 'Not available for POS'}
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] uppercase tracking-[.05em] text-[#8A8A84]">
                  Selling price
                </div>
                <div className="font-serif text-base font-bold text-[#1A7A4A]">
                  {formatINR(row.selling_price)}
                </div>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setEditAssignment(row);
                  setEditPrice(String(row.selling_price));
                }}
              >
                Edit price
              </Button>
              <button
                type="button"
                onClick={() =>
                  updateAssignmentMutation.mutate({
                    franchise_id: row.franchise_id,
                    is_active: !row.is_active,
                  })
                }
                className="rounded-md border border-[#E0DDD5] px-2.5 py-1 text-[11px] font-semibold"
                style={{
                  background: row.is_active ? '#E6F4EC' : '#FDFAF4',
                  color: row.is_active ? '#1A7A4A' : '#8A8A84',
                }}
              >
                {row.is_active ? 'Assignment Active' : 'Assignment Hidden'}
              </button>
            </div>
          ))}
        </div>
      )}

      {showAssign ? (
        <Modal title="Assign to franchise" onClose={() => setShowAssign(false)}>
          <SelectField
            label="Franchise"
            value={franchiseId}
            onChange={(e) => setFranchiseId(e.target.value)}
          >
            <option value="">Select franchise</option>
            {unassignedFranchises.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </SelectField>
          <Field
            label="Franchise Selling Price (₹)"
            type="number"
            min={0.01}
            step="0.01"
            value={sellingPrice}
            error={sellingPrice ? sellingPriceError(sellingPrice, product.price) ?? undefined : undefined}
            onChange={(e) => setSellingPrice(e.target.value)}
          />
          <label className="mb-3 flex items-center gap-2 text-sm text-[#4A4A46]">
            <input
              type="checkbox"
              checked={assignActive}
              onChange={(event) => setAssignActive(event.target.checked)}
            />
            Assignment Active (uncheck to hide from this franchise POS)
          </label>
          <p className="mb-3 text-[11px] text-[#8A8A84]">
            Master price for this item: {formatINR(product.price)}. Selling price must be greater
            than 0 and strictly less than the master price.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={() => setShowAssign(false)}>
              Cancel
            </Button>
            <Button
              disabled={
                !franchiseId ||
                Boolean(sellingPriceError(sellingPrice, product.price)) ||
                assignMutation.isPending
              }
              onClick={() => assignMutation.mutate()}
            >
              {assignMutation.isPending ? 'Saving…' : 'Assign'}
            </Button>
          </div>
        </Modal>
      ) : null}

      {editAssignment ? (
        <Modal title="Edit franchise selling price" onClose={() => setEditAssignment(null)}>
          <p className="mb-3 text-sm text-[#5C5C56]">
            {editAssignment.franchise_name} · Master {formatINR(product.price)}
          </p>
          <Field
            label="Franchise Selling Price (₹)"
            type="number"
            min={0.01}
            step="0.01"
            value={editPrice}
            error={sellingPriceError(editPrice, product.price) ?? undefined}
            onChange={(e) => setEditPrice(e.target.value)}
          />
          <p className="mb-3 text-[11px] text-[#8A8A84]">
            Must be greater than 0 and strictly less than the master price.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={() => setEditAssignment(null)}>
              Cancel
            </Button>
            <Button
              disabled={
                Boolean(sellingPriceError(editPrice, product.price)) ||
                updateAssignmentMutation.isPending
              }
              onClick={() =>
                updateAssignmentMutation.mutate({
                  franchise_id: editAssignment.franchise_id,
                  selling_price: Number(editPrice),
                })
              }
            >
              {updateAssignmentMutation.isPending ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
