export type ProductCategory = {
  id: string;
  name: string;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ProductCategoryListResponse = {
  items: ProductCategory[];
  total: number;
};

export type Product = {
  id: string;
  category_id: string | null;
  sku: string | null;
  name: string;
  description: string | null;
  image_url: string | null;
  price: number;
  min_price: number | null;
  max_price: number | null;
  is_active: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  category?: Pick<ProductCategory, 'id' | 'name' | 'display_order' | 'is_active'> | null;
};

export type ProductWritePayload = {
  name: string;
  category_id: string;
  description?: string | null;
  price: number;
  sku?: string | null;
  is_active?: boolean;
};

export type FranchiseProductAssignment = {
  id: string;
  franchise_id: string;
  product_id: string;
  selling_price: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  product_name: string | null;
  product_description: string | null;
  product_is_active: boolean | null;
  master_price: number | null;
  category_id: string | null;
  category_name: string | null;
  image_url: string | null;
  category_is_active?: boolean | null;
  available_for_pos: boolean;
  price_editable?: boolean;
};

export type FranchiseProductAssignPayload = {
  product_id: string;
  selling_price: number;
  is_active?: boolean;
};

export type FranchiseProductUpdatePayload = {
  selling_price?: number;
  is_active?: boolean;
};

export type OwnerMenuUpdatePayload = {
  selling_price: number;
};

export function sellingPriceError(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return 'Franchise selling price is required.';
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) {
    return 'Enter a valid price with up to 2 decimal places.';
  }
  const amount = Number(trimmed);
  if (Number.isNaN(amount) || amount <= 0) {
    return 'Selling price must be greater than 0.';
  }
  return null;
}

export function productImageUrl(
  product: Pick<Product, 'image_url' | 'metadata'> | { image_url?: string | null },
): string | null {
  if (product.image_url) return product.image_url;
  if ('metadata' in product && product.metadata && typeof product.metadata.image_url === 'string') {
    return product.metadata.image_url;
  }
  return null;
}

export function formatINR(amount: number | null | undefined): string {
  if (amount == null || Number.isNaN(amount)) return '—';
  return `₹${Number(amount).toLocaleString('en-IN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}

export function ownerCanEditSellingPrice(
  item: Pick<FranchiseProductAssignment, 'is_active' | 'product_is_active' | 'price_editable'>,
): boolean {
  if (typeof item.price_editable === 'boolean') return item.price_editable;
  return item.is_active === true && item.product_is_active === true;
}
