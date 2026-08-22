import { useRef, useState, type FormEvent } from 'react';

import { Button, Field, SelectField } from '../../components/ui';
import { validatePrice, validateRequiredText } from '../../lib/validation';
import type { Product, ProductCategory, ProductWritePayload } from '../../types/product';
import { ProductImage } from './ProductImage';

const ACCEPTED = 'image/jpeg,image/jpg,image/png,image/webp';
const MAX_BYTES = 5 * 1024 * 1024;

export type ProductFormValues = {
  name: string;
  description: string;
  price: string;
  category_id: string;
  is_active: boolean;
};

export function emptyProductForm(defaultCategoryId = ''): ProductFormValues {
  return {
    name: '',
    description: '',
    price: '',
    category_id: defaultCategoryId,
    is_active: true,
  };
}

export function productToForm(product: Product): ProductFormValues {
  return {
    name: product.name,
    description: product.description ?? '',
    price: String(product.price),
    category_id: product.category_id ?? '',
    is_active: product.is_active,
  };
}

export function toProductPayload(values: ProductFormValues): ProductWritePayload {
  return {
    name: values.name.trim(),
    category_id: values.category_id,
    description: values.description.trim() || null,
    price: Number(values.price),
    is_active: values.is_active,
  };
}

export function ProductForm({
  categories,
  initial,
  submitLabel,
  busy,
  existingImageUrl,
  pendingFile,
  onPendingFileChange,
  onRemoveExistingImage,
  removingImage,
  onSubmit,
  onCancel,
}: {
  categories: ProductCategory[];
  initial: ProductFormValues;
  submitLabel: string;
  busy?: boolean;
  existingImageUrl?: string | null;
  pendingFile?: File | null;
  onPendingFileChange?: (file: File | null) => void;
  onRemoveExistingImage?: () => void;
  removingImage?: boolean;
  onSubmit: (values: ProductFormValues) => void;
  onCancel: () => void;
}) {
  const [values, setValues] = useState<ProductFormValues>(initial);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof ProductFormValues, string>>>({});
  const [localPreview, setLocalPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const update = <K extends keyof ProductFormValues>(key: K, value: ProductFormValues[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    if (fieldErrors[key]) {
      setFieldErrors((current) => {
        const next = { ...current };
        delete next[key];
        return next;
      });
    }
  };

  const handleFile = (file: File | null) => {
    if (!file) {
      setLocalPreview(null);
      onPendingFileChange?.(null);
      return;
    }
    const type = file.type.toLowerCase();
    if (!['image/jpeg', 'image/jpg', 'image/png', 'image/webp'].includes(type)) {
      setError('Unsupported image type. Use JPG, PNG, or WEBP.');
      return;
    }
    if (file.size > MAX_BYTES) {
      setError('Image must be 5 MB or smaller.');
      return;
    }
    setError(null);
    setLocalPreview(URL.createObjectURL(file));
    onPendingFileChange?.(file);
  };

  const assignableCategories = categories.filter(
    (c) => c.is_active || c.id === values.category_id,
  );

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const nextErrors: Partial<Record<keyof ProductFormValues, string>> = {};
    const nameError = validateRequiredText(values.name, 'Item name is required.');
    if (nameError) nextErrors.name = nameError;
    if (!values.category_id) {
      nextErrors.category_id = 'Category is required.';
    }
    const selected = categories.find((c) => c.id === values.category_id);
    if (!selected && values.category_id) {
      nextErrors.category_id = 'Category is required.';
    }
    if (selected && !selected.is_active && selected.id !== initial.category_id) {
      nextErrors.category_id = 'Select an active category.';
    }
    const priceError = validatePrice(values.price, {
      requiredMessage: 'Master price is required.',
      invalidMessage: 'Enter a valid price with up to 2 decimal places.',
      minMessage: 'Enter a valid master price (₹), zero or greater.',
      allowZero: true,
      requirePositive: false,
    });
    if (priceError) nextErrors.price = priceError;
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      setError(null);
      return;
    }
    setError(null);
    onSubmit(values);
  };

  const previewSrc = localPreview || existingImageUrl || null;

  return (
    <form onSubmit={handleSubmit}>
      <Field
        label="Item Name"
        value={values.name}
        onChange={(e) => update('name', e.target.value)}
        error={fieldErrors.name}
        required
      />
      <Field
        label="Description"
        value={values.description}
        onChange={(e) => update('description', e.target.value)}
      />
      <Field
        label="Master Price (₹)"
        type="number"
        min={0}
        step="0.01"
        value={values.price}
        onChange={(e) => update('price', e.target.value)}
        error={fieldErrors.price}
        required
      />
      <p className="mb-3 -mt-2 text-[11px] text-[#8A8A84]">
        Catalog / base price. Franchise selling price is set per outlet.
      </p>

      <SelectField
        label="Category"
        value={values.category_id}
        onChange={(e) => update('category_id', e.target.value)}
        error={fieldErrors.category_id}
        required
        disabled={!assignableCategories.length}
      >
        <option value="">Select category</option>
        {assignableCategories.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
            {!c.is_active ? ' (inactive)' : ''}
          </option>
        ))}
      </SelectField>

      <div className="mb-3">
        <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
          Product Image
        </div>
        <div className="flex items-start gap-3 rounded-lg border border-[#E0DDD5] bg-[#FDFAF4] p-3">
          <ProductImage src={previewSrc} alt={values.name || 'Product'} size="lg" />
          <div className="min-w-0 flex-1">
            <p className="mb-2 text-[11px] text-[#8A8A84]">JPG, PNG, or WEBP · max 5 MB</p>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED}
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
            />
            <div className="flex flex-wrap gap-2">
              <Button type="button" size="sm" variant="outline" onClick={() => inputRef.current?.click()}>
                {previewSrc ? 'Replace image' : 'Upload image'}
              </Button>
              {pendingFile ? (
                <Button type="button" size="sm" variant="muted" onClick={() => handleFile(null)}>
                  Clear selection
                </Button>
              ) : null}
              {!pendingFile && existingImageUrl && onRemoveExistingImage ? (
                <Button
                  type="button"
                  size="sm"
                  variant="muted"
                  disabled={removingImage}
                  onClick={onRemoveExistingImage}
                >
                  {removingImage ? 'Removing…' : 'Remove image'}
                </Button>
              ) : null}
            </div>
            {pendingFile ? (
              <p className="mt-2 truncate text-[11px] text-[#5C5C56]">{pendingFile.name}</p>
            ) : null}
          </div>
        </div>
      </div>

      {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button type="button" variant="muted" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
        <Button type="submit" disabled={busy || !assignableCategories.length}>
          {busy ? 'Saving…' : submitLabel}
        </Button>
      </div>
    </form>
  );
}
