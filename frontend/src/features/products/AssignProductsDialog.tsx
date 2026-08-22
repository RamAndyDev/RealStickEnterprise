import { useEffect, useMemo, useRef, useState } from 'react';

import { Button, EmptyState, ErrorBanner, LoadingBlock, Modal } from '../../components/ui';
import { assignFranchiseProduct, updateFranchiseProduct } from '../../lib/productsApi';
import {
  formatINR,
  sellingPriceError,
  type FranchiseProductAssignment,
  type Product,
} from '../../types/product';
import { apiErrorMessage } from '../franchises/status';
import {
  UNCATEGORIZED_ID,
  UNCATEGORIZED_NAME,
  buildAssignmentSavePlan,
  categorySelectionState,
  draftValidationErrors,
  filterGroupedProducts,
  groupProductsByCategory,
  initialAssignDraft,
  setCategorySelected,
  setProductSelected,
  setProductSellingPrice,
  type AssignDraft,
  type AssignProductRow,
  type AssignmentSnapshot,
} from './assignProducts';
import { categoryColor } from './categoryColors';

const CHECKBOX_CLASS =
  'h-4 w-4 shrink-0 accent-[#1A7A4A] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A]';

function toAssignProductRow(product: Product): AssignProductRow {
  return {
    id: product.id,
    name: product.name,
    price: product.price,
    categoryId: product.category_id ?? product.category?.id ?? UNCATEGORIZED_ID,
    categoryName: product.category?.name ?? UNCATEGORIZED_NAME,
    categoryOrder: product.category?.display_order ?? Number.MAX_SAFE_INTEGER,
  };
}

function snapshotsFromAssignments(
  assignments: FranchiseProductAssignment[],
): Map<string, AssignmentSnapshot> {
  const snapshots = new Map<string, AssignmentSnapshot>();
  for (const assignment of assignments) {
    snapshots.set(assignment.product_id, {
      productId: assignment.product_id,
      sellingPrice: assignment.selling_price,
      isActive: assignment.is_active,
    });
  }
  return snapshots;
}

type AssignProductsDialogProps = {
  franchiseId: string;
  franchiseName?: string;
  products: Product[];
  assignments: FranchiseProductAssignment[];
  loading?: boolean;
  loadError?: string | null;
  onClose: () => void;
  onSaved: () => void;
};

export function AssignProductsDialog({
  franchiseId,
  franchiseName,
  products,
  assignments,
  loading = false,
  loadError = null,
  onClose,
  onSaved,
}: AssignProductsDialogProps) {
  const rows = useMemo(() => products.map(toAssignProductRow), [products]);
  const snapshots = useMemo(() => snapshotsFromAssignments(assignments), [assignments]);
  const groups = useMemo(() => groupProductsByCategory(rows), [rows]);

  const [search, setSearch] = useState('');
  const [draft, setDraft] = useState<AssignDraft>(() => initialAssignDraft(rows, snapshots));
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [showValidation, setShowValidation] = useState(false);
  const savingRef = useRef(false);

  useEffect(() => {
    setDraft((current) => {
      const next = initialAssignDraft(rows, snapshots);
      for (const [id, item] of Object.entries(current)) {
        if (next[id]) next[id] = item;
      }
      return next;
    });
  }, [rows, snapshots]);

  const visibleGroups = useMemo(() => filterGroupedProducts(groups, search), [groups, search]);
  const validationErrors = useMemo(
    () => draftValidationErrors(rows, draft, sellingPriceError),
    [rows, draft],
  );
  const hasValidationErrors = Object.keys(validationErrors).length > 0;

  const persist = async () => {
    if (savingRef.current) return;
    setShowValidation(true);
    setSaveError(null);
    const errors = draftValidationErrors(rows, draft, sellingPriceError);
    if (Object.keys(errors).length) return;

    const plan = buildAssignmentSavePlan(rows, draft, snapshots);
    savingRef.current = true;
    setSaving(true);
    try {
      for (const action of plan) {
        if (action.type === 'create') {
          await assignFranchiseProduct(franchiseId, {
            product_id: action.productId,
            selling_price: action.sellingPrice,
            is_active: true,
          });
          continue;
        }
        if (action.type === 'deactivate') {
          await updateFranchiseProduct(franchiseId, action.productId, { is_active: false });
          continue;
        }
        if (action.type === 'activate') {
          await updateFranchiseProduct(franchiseId, action.productId, {
            is_active: true,
            ...(action.sellingPrice != null ? { selling_price: action.sellingPrice } : {}),
          });
          continue;
        }
        await updateFranchiseProduct(franchiseId, action.productId, {
          selling_price: action.sellingPrice,
        });
      }
      onSaved();
    } catch (err) {
      setSaveError(apiErrorMessage(err, 'Unable to save product assignments.'));
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  const subtitle = (
    <div>
      {franchiseName ? (
        <p className="font-medium text-[#1A1A18]">
          Assign products to: <span className="text-[#1A7A4A]">{franchiseName}</span>
        </p>
      ) : null}
      <p>Select the products available at this franchise.</p>
    </div>
  );

  return (
    <Modal
      title="Assign Products"
      subtitle={subtitle}
      size="lg"
      onClose={onClose}
      toolbar={
        <label className="block">
          <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
            Search products
          </span>
          <input
            type="search"
            value={search}
            disabled={saving}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search products..."
            autoComplete="off"
            className="w-full rounded-lg border border-[#E0DDD5] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1A7A4A] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A]"
          />
        </label>
      }
      footer={
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
          {showValidation && hasValidationErrors ? (
            <p className="text-xs text-red-600 sm:mr-auto">
              Fix selling prices that are not greater than 0 before saving.
            </p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button
              onClick={() => void persist()}
              disabled={saving || loading || Boolean(loadError) || (showValidation && hasValidationErrors)}
              aria-disabled={saving || loading || Boolean(loadError) || (showValidation && hasValidationErrors)}
            >
              {saving ? 'Saving…' : 'Save Assignments'}
            </Button>
          </div>
        </div>
      }
    >
      {loading ? <LoadingBlock label="Loading products…" /> : null}
      {loadError ? <ErrorBanner message={loadError} /> : null}
      {saveError ? (
        <div className="mb-3">
          <ErrorBanner message={saveError} />
        </div>
      ) : null}

      {!loading && !loadError && !rows.length ? (
        <EmptyState title="No products available." />
      ) : null}

      {!loading && !loadError && rows.length > 0 && !visibleGroups.length ? (
        <EmptyState title="No products match your search." />
      ) : null}

      {!loading && !loadError
        ? visibleGroups.map((group) => {
            const productIds = group.products.map((product) => product.id);
            const selection = categorySelectionState(productIds, draft);
            const selectedCount = productIds.filter((id) => draft[id]?.selected).length;
            const color = categoryColor(group.name);
            return (
              <section key={group.id} className="mb-3.5 last:mb-0">
                <div
                  className="mb-1.5 flex flex-wrap items-center justify-between gap-2"
                  style={{ color }}
                >
                  <label className="flex min-w-0 items-center gap-2 text-[10px] font-semibold uppercase tracking-[.08em]">
                    <input
                      type="checkbox"
                      className={CHECKBOX_CLASS}
                      checked={selection === 'all'}
                      aria-checked={selection === 'some' ? 'mixed' : selection === 'all'}
                      aria-label={`Select all products in ${group.name}`}
                      ref={(element) => {
                        if (element) element.indeterminate = selection === 'some';
                      }}
                      disabled={saving}
                      onChange={(event) =>
                        setDraft((current) =>
                          setCategorySelected(current, productIds, event.target.checked),
                        )
                      }
                    />
                    <span className="truncate">{group.name}</span>
                  </label>
                  <span className="text-[10px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
                    {selectedCount} / {productIds.length} selected
                  </span>
                </div>
                <div className="overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white">
                  {group.products.map((product, index) => {
                    const item = draft[product.id] ?? { selected: false, sellingPrice: '' };
                    const priceError = item.selected
                      ? validationErrors[product.id]
                      : undefined;
                    const showError = Boolean(showValidation && priceError);
                    return (
                      <div
                        key={product.id}
                        className="px-3.5 py-2.5"
                        style={{
                          borderBottom:
                            index < group.products.length - 1 ? '1px solid #E0DDD5' : undefined,
                        }}
                      >
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                          <label className="flex min-w-0 items-start gap-2.5">
                            <input
                              type="checkbox"
                              className={`${CHECKBOX_CLASS} mt-0.5`}
                              checked={item.selected}
                              disabled={saving}
                              onChange={(event) =>
                                setDraft((current) =>
                                  setProductSelected(current, product.id, event.target.checked),
                                )
                              }
                            />
                            <span className="min-w-0">
                              <span className="block text-[13px] font-medium text-[#1A1A18]">
                                {product.name}
                              </span>
                              <span className="mt-0.5 block text-[11px] text-[#8A8A84]">
                                Master Price {formatINR(product.price)}
                              </span>
                              <span className="block text-[10px] text-[#8A8A84]">
                                Master Price is for reference only.
                              </span>
                            </span>
                          </label>
                          <div className="min-w-0 sm:w-[11.5rem] sm:pl-2">
                            {item.selected ? (
                              <label className="block">
                                <span className="mb-1 block text-[10px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
                                  Selling price
                                </span>
                                <input
                                  type="number"
                                  min={0.01}
                                  step="0.01"
                                  inputMode="decimal"
                                  value={item.sellingPrice}
                                  disabled={saving}
                                  aria-invalid={showError}
                                  aria-describedby={
                                    showError ? `selling-error-${product.id}` : undefined
                                  }
                                  onChange={(event) => {
                                    setShowValidation(true);
                                    setDraft((current) =>
                                      setProductSellingPrice(
                                        current,
                                        product.id,
                                        event.target.value,
                                      ),
                                    );
                                  }}
                                  className={`w-full rounded-lg border bg-white px-2.5 py-1.5 text-sm outline-none focus:border-[#1A7A4A] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A] ${
                                    showError ? 'border-red-500' : 'border-[#E0DDD5]'
                                  }`}
                                />
                                <span className="mt-1 block text-[10px] text-[#8A8A84]">
                                  Set the selling price for this franchise.
                                </span>
                              </label>
                            ) : (
                              <p className="text-[11px] text-[#8A8A84] sm:pt-0.5 sm:text-right">
                                Selling Not assigned
                              </p>
                            )}
                          </div>
                        </div>
                        {showError ? (
                          <p
                            id={`selling-error-${product.id}`}
                            className="mt-1 pl-6 text-xs text-red-600"
                          >
                            {priceError}
                          </p>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </section>
            );
          })
        : null}
    </Modal>
  );
}
