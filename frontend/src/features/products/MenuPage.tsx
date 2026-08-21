import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
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
  createProduct,
  createProductCategory,
  listProductCategories,
  listProducts,
  removeProductImage,
  updateProduct,
  updateProductCategory,
  uploadProductImage,
} from '../../lib/productsApi';
import { formatINR, type Product, type ProductCategory } from '../../types/product';
import { apiErrorMessage } from '../franchises/status';
import { categoryColor } from './categoryColors';
import {
  ProductForm,
  emptyProductForm,
  productToForm,
  toProductPayload,
  type ProductFormValues,
} from './ProductForm';
import { ProductImage } from './ProductImage';

export function MenuPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('All');
  const [showAdd, setShowAdd] = useState(false);
  const [editTarget, setEditTarget] = useState<Product | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [editCategory, setEditCategory] = useState<ProductCategory | null>(null);
  const [categoryName, setCategoryName] = useState('');
  const [categoryOrder, setCategoryOrder] = useState('0');
  const [categoryActive, setCategoryActive] = useState(true);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => window.clearTimeout(handle);
  }, [search]);

  const categoriesQuery = useQuery({
    queryKey: ['admin-product-categories'],
    queryFn: () => listProductCategories(true),
  });

  const productsQuery = useQuery({
    queryKey: ['admin-products', debouncedSearch],
    queryFn: () => listProducts({ search: debouncedSearch || undefined }),
  });

  const categories = useMemo(() => {
    const items = [...(categoriesQuery.data?.items ?? [])];
    items.sort((a, b) => a.display_order - b.display_order || a.name.localeCompare(b.name));
    return items;
  }, [categoriesQuery.data]);

  const activeCategories = categories.filter((c) => c.is_active);
  const products = productsQuery.data?.items ?? [];

  const filtered = useMemo(() => {
    if (activeCategory === 'All') return products;
    return products.filter((p) => p.category?.name === activeCategory);
  }, [products, activeCategory]);

  const grouped = useMemo(
    () =>
      categories.map((category) => ({
        category,
        items: filtered.filter((p) => p.category_id === category.id),
      })),
    [categories, filtered],
  );

  const activeCount = products.filter((p) => p.is_active).length;
  const hiddenCount = products.length - activeCount;

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ['admin-products'] });
    await queryClient.invalidateQueries({ queryKey: ['admin-product'] });
    await queryClient.invalidateQueries({ queryKey: ['admin-product-categories'] });
  };

  const createMutation = useMutation({
    mutationFn: async (values: ProductFormValues) => {
      const created = await createProduct(toProductPayload(values));
      if (pendingFile) {
        return uploadProductImage(created.id, pendingFile);
      }
      return created;
    },
    onSuccess: async () => {
      setShowAdd(false);
      setPendingFile(null);
      setFeedback('Item added successfully.');
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to add item.')),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, values }: { id: string; values: ProductFormValues }) => {
      const updated = await updateProduct(id, toProductPayload(values));
      if (pendingFile) {
        return uploadProductImage(id, pendingFile);
      }
      return updated;
    },
    onSuccess: async () => {
      setEditTarget(null);
      setPendingFile(null);
      setFeedback('Item updated successfully.');
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update item.')),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateProduct(id, { is_active }),
    onSuccess: async (data) => {
      setFeedback(data.is_active ? 'Item set to Active.' : 'Item set to Hidden.');
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to change availability.')),
  });

  const removeImageMutation = useMutation({
    mutationFn: (id: string) => removeProductImage(id),
    onSuccess: async (data) => {
      setEditTarget(data);
      setFeedback('Product image removed.');
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to remove image.')),
  });

  const createCategoryMutation = useMutation({
    mutationFn: () =>
      createProductCategory({
        name: categoryName.trim(),
        display_order: Number(categoryOrder) || 0,
        is_active: categoryActive,
      }),
    onSuccess: async () => {
      setShowCategoryModal(false);
      setCategoryName('');
      setFeedback('Category created.');
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to create category.')),
  });

  const updateCategoryMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Partial<{ name: string; display_order: number; is_active: boolean }>;
    }) => updateProductCategory(id, payload),
    onSuccess: async (_data, variables) => {
      setEditCategory(null);
      if (variables.payload.is_active === false) {
        setFeedback('Category deactivated. Products in this category are now inactive.');
      } else if (variables.payload.is_active === true) {
        setFeedback('Category activated. Products remain inactive until you enable them.');
      } else {
        setFeedback('Category updated.');
      }
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update category.')),
  });

  const defaultCategoryId = activeCategories[0]?.id ?? '';

  if (categoriesQuery.isLoading || productsQuery.isLoading) {
    return <LoadingBlock label="Loading menu…" />;
  }

  if (categoriesQuery.isError || productsQuery.isError) {
    return (
      <ErrorBanner
        message={apiErrorMessage(
          categoriesQuery.error ?? productsQuery.error,
          'Unable to load menu.',
        )}
      />
    );
  }

  const chips = ['All', ...categories.map((c) => c.name)];

  return (
    <div className="mx-auto max-w-[840px]">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-serif text-[20px] font-bold text-[#1A1A18]">Menu Management</h1>
          <p className="text-xs text-[#8A8A84]">
            {activeCount} active · {hiddenCount} hidden
          </p>
        </div>
        <Button
          onClick={() => {
            setPendingFile(null);
            setShowAdd(true);
          }}
          disabled={!activeCategories.length}
        >
          + Add Item
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

      {/* Categories */}
      <section className="mb-5">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="font-serif text-base font-bold text-[#1A1A18]">Categories</h2>
            <p className="text-[11px] text-[#8A8A84]">
              Initial RealStick menus plus any additional categories you add
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setCategoryName('');
              setCategoryOrder(String((categories.length + 1) * 10));
              setCategoryActive(true);
              setShowCategoryModal(true);
            }}
          >
            + Add Category
          </Button>
        </div>
        <div className="overflow-x-auto rounded-[10px] border border-[#E0DDD5] bg-white">
          <div className="grid min-w-[520px] grid-cols-[1.4fr_0.7fr_0.5fr_auto] gap-2 border-b border-[#E0DDD5] bg-[#FDFAF4] px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
            <div>Category Name</div>
            <div>Status</div>
            <div>Order</div>
            <div className="text-right">Actions</div>
          </div>
          {categories.map((category, idx) => (
            <div
              key={category.id}
              className="grid min-w-[520px] grid-cols-[1.4fr_0.7fr_0.5fr_auto] items-center gap-2 px-3.5 py-2.5"
              style={{
                borderBottom: idx < categories.length - 1 ? '1px solid #E0DDD5' : undefined,
                opacity: category.is_active ? 1 : 0.55,
              }}
            >
              <div
                className="truncate text-[13px] font-medium"
                style={{ color: categoryColor(category.name) }}
              >
                {category.name}
              </div>
              <div className="text-[11px] font-semibold text-[#5C5C56]">
                {category.is_active ? 'Active' : 'Inactive'}
              </div>
              <div className="text-[12px] text-[#1A1A18]">{category.display_order}</div>
              <ActionGroup align="end">
                <ActionButton
                  variant="outline"
                  onClick={() => {
                    setEditCategory(category);
                    setCategoryName(category.name);
                    setCategoryOrder(String(category.display_order));
                    setCategoryActive(category.is_active);
                  }}
                >
                  Edit
                </ActionButton>
                <ActionButton
                  fit="status"
                  variant={category.is_active ? 'muted' : 'outline'}
                  onClick={() =>
                    updateCategoryMutation.mutate({
                      id: category.id,
                      payload: { is_active: !category.is_active },
                    })
                  }
                >
                  {category.is_active ? 'Deactivate' : 'Activate'}
                </ActionButton>
              </ActionGroup>
            </div>
          ))}
          {!categories.length ? (
            <div className="px-4 py-6 text-center text-xs text-[#8A8A84]">No categories yet</div>
          ) : null}
        </div>
      </section>

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
                onClick={() => {
                  setActiveCategory(chip);
                  setSearch('');
                }}
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

      {grouped.map(({ category, items }) => {
        if (activeCategory !== 'All' && category.name !== activeCategory) return null;
        if (debouncedSearch && !items.length) return null;
        return (
          <div key={category.id} className="mb-3.5">
            <div
              className="mb-1.5 text-[10px] font-semibold uppercase tracking-[.08em]"
              style={{ color: categoryColor(category.name) }}
            >
              {category.name} ({items.length})
              {!category.is_active ? ' · inactive' : ''}
            </div>
            <div className="overflow-hidden rounded-[10px] border border-[#E0DDD5] bg-white">
              {!items.length ? (
                <div className="px-4 py-6 text-center text-xs text-[#8A8A84]">No items</div>
              ) : (
                items.map((item, idx) => (
                  <div
                    key={item.id}
                    className="flex flex-wrap items-center gap-2.5 px-3.5 py-2.5"
                    style={{
                      borderBottom: idx < items.length - 1 ? '1px solid #E0DDD5' : undefined,
                      opacity: item.is_active ? 1 : 0.5,
                    }}
                  >
                    <ProductImage product={item} size="sm" />
                    <div className="min-w-0 flex-1">
                      <Link
                        to={`/products/${item.id}`}
                        className="block truncate text-[13px] font-medium text-[#1A1A18] hover:text-[#1A7A4A]"
                      >
                        {item.name}
                      </Link>
                      <div className="truncate text-[10px] text-[#8A8A84]">
                        {item.description || '—'}
                      </div>
                    </div>
                    <div className="min-w-[42px] text-right font-serif text-sm font-bold text-[#1A7A4A]">
                      {formatINR(item.price)}
                    </div>
                    <ActionGroup>
                      <ActionButton
                        variant="outline"
                        onClick={() => {
                          setPendingFile(null);
                          setEditTarget(item);
                        }}
                      >
                        Edit
                      </ActionButton>
                      <ActionButton
                        fit="md"
                        variant={item.is_active ? 'outline' : 'muted'}
                        onClick={() =>
                          toggleMutation.mutate({ id: item.id, is_active: !item.is_active })
                        }
                      >
                        {item.is_active ? 'Active' : 'Hidden'}
                      </ActionButton>
                    </ActionGroup>
                  </div>
                ))
              )}
            </div>
          </div>
        );
      })}

      {debouncedSearch && !filtered.length ? (
        <EmptyState title="No items found" hint="Try a different search term." />
      ) : null}

      {showAdd ? (
        <Modal
          title="Add Item"
          onClose={() => {
            setShowAdd(false);
            setPendingFile(null);
          }}
        >
          <ProductForm
            categories={categories}
            initial={emptyProductForm(defaultCategoryId)}
            submitLabel="Save"
            busy={createMutation.isPending}
            pendingFile={pendingFile}
            onPendingFileChange={setPendingFile}
            onCancel={() => {
              setShowAdd(false);
              setPendingFile(null);
            }}
            onSubmit={(values) => createMutation.mutate(values)}
          />
        </Modal>
      ) : null}

      {editTarget ? (
        <Modal
          title="Edit Item"
          onClose={() => {
            setEditTarget(null);
            setPendingFile(null);
          }}
        >
          <ProductForm
            categories={categories}
            initial={productToForm(editTarget)}
            submitLabel="Save"
            busy={updateMutation.isPending}
            existingImageUrl={editTarget.image_url}
            pendingFile={pendingFile}
            onPendingFileChange={setPendingFile}
            removingImage={removeImageMutation.isPending}
            onRemoveExistingImage={() => removeImageMutation.mutate(editTarget.id)}
            onCancel={() => {
              setEditTarget(null);
              setPendingFile(null);
            }}
            onSubmit={(values) => updateMutation.mutate({ id: editTarget.id, values })}
          />
        </Modal>
      ) : null}

      {showCategoryModal ? (
        <Modal title="Add Category" onClose={() => setShowCategoryModal(false)}>
          <Field
            label="Category Name"
            value={categoryName}
            onChange={(e) => setCategoryName(e.target.value)}
            placeholder="e.g. Summer Specials"
          />
          <Field
            label="Display Order"
            type="number"
            min={0}
            value={categoryOrder}
            onChange={(e) => setCategoryOrder(e.target.value)}
          />
          <label className="mb-3 flex items-center gap-2 text-sm text-[#1A1A18]">
            <input
              type="checkbox"
              checked={categoryActive}
              onChange={(e) => setCategoryActive(e.target.checked)}
            />
            Active
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={() => setShowCategoryModal(false)}>
              Cancel
            </Button>
            <Button
              disabled={!categoryName.trim() || createCategoryMutation.isPending}
              onClick={() => createCategoryMutation.mutate()}
            >
              {createCategoryMutation.isPending ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </Modal>
      ) : null}

      {editCategory ? (
        <Modal title="Edit Category" onClose={() => setEditCategory(null)}>
          <Field
            label="Category Name"
            value={categoryName}
            onChange={(e) => setCategoryName(e.target.value)}
          />
          <Field
            label="Display Order"
            type="number"
            min={0}
            value={categoryOrder}
            onChange={(e) => setCategoryOrder(e.target.value)}
          />
          <label className="mb-3 flex items-center gap-2 text-sm text-[#1A1A18]">
            <input
              type="checkbox"
              checked={categoryActive}
              onChange={(e) => setCategoryActive(e.target.checked)}
            />
            Active
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="muted" onClick={() => setEditCategory(null)}>
              Cancel
            </Button>
            <Button
              disabled={!categoryName.trim() || updateCategoryMutation.isPending}
              onClick={() =>
                updateCategoryMutation.mutate({
                  id: editCategory.id,
                  payload: {
                    name: categoryName.trim(),
                    display_order: Number(categoryOrder) || 0,
                    is_active: categoryActive,
                  },
                })
              }
            >
              {updateCategoryMutation.isPending ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
