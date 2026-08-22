import type {
  FranchiseProductAssignPayload,
  FranchiseProductAssignment,
  FranchiseProductUpdatePayload,
  OwnerMenuUpdatePayload,
  Product,
  ProductCategory,
  ProductCategoryListResponse,
  ProductWritePayload,
} from '../types/product';
import { api } from './api';

export async function listProductCategories(includeInactive = true): Promise<ProductCategoryListResponse> {
  const { data } = await api.get<ProductCategoryListResponse>('/admin/product-categories', {
    params: { include_inactive: includeInactive },
  });
  return data;
}

export async function createProductCategory(payload: {
  name: string;
  display_order?: number;
  is_active?: boolean;
}): Promise<ProductCategory> {
  const { data } = await api.post<ProductCategory>('/admin/product-categories', payload);
  return data;
}

export async function updateProductCategory(
  id: string,
  payload: Partial<{ name: string; display_order: number; is_active: boolean }>,
): Promise<ProductCategory> {
  const { data } = await api.patch<ProductCategory>(`/admin/product-categories/${id}`, payload);
  return data;
}

export type ProductListParams = {
  category_id?: string;
  search?: string;
  is_active?: boolean;
};

export async function listProducts(params: ProductListParams = {}): Promise<{
  items: Product[];
  total: number;
}> {
  const { data } = await api.get<{ items: Product[]; total: number }>('/admin/products', {
    params: {
      category_id: params.category_id || undefined,
      search: params.search || undefined,
      is_active: params.is_active,
    },
  });
  return data;
}

export async function getProduct(id: string): Promise<Product> {
  const { data } = await api.get<Product>(`/admin/products/${id}`);
  return data;
}

export async function createProduct(payload: ProductWritePayload): Promise<Product> {
  const { data } = await api.post<Product>('/admin/products', payload);
  return data;
}

export async function updateProduct(
  id: string,
  payload: Partial<ProductWritePayload>,
): Promise<Product> {
  const { data } = await api.patch<Product>(`/admin/products/${id}`, payload);
  return data;
}

export async function deleteProduct(id: string): Promise<void> {
  await api.delete(`/admin/products/${id}`);
}

export async function uploadProductImage(id: string, file: File): Promise<Product> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<Product>(`/admin/products/${id}/image`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function removeProductImage(id: string): Promise<Product> {
  const { data } = await api.delete<Product>(`/admin/products/${id}/image`);
  return data;
}

export async function listFranchiseProducts(franchiseId: string): Promise<{
  items: FranchiseProductAssignment[];
  total: number;
}> {
  const { data } = await api.get<{ items: FranchiseProductAssignment[]; total: number }>(
    `/admin/franchises/${franchiseId}/products`,
  );
  return data;
}

export async function assignFranchiseProduct(
  franchiseId: string,
  payload: FranchiseProductAssignPayload,
): Promise<FranchiseProductAssignment> {
  const { data } = await api.post<FranchiseProductAssignment>(
    `/admin/franchises/${franchiseId}/products`,
    payload,
  );
  return data;
}

export async function updateFranchiseProduct(
  franchiseId: string,
  productId: string,
  payload: FranchiseProductUpdatePayload,
): Promise<FranchiseProductAssignment> {
  const { data } = await api.patch<FranchiseProductAssignment>(
    `/admin/franchises/${franchiseId}/products/${productId}`,
    payload,
  );
  return data;
}

export async function listOwnerMenu(): Promise<{
  items: FranchiseProductAssignment[];
  total: number;
}> {
  const { data } = await api.get<{ items: FranchiseProductAssignment[]; total: number }>(
    '/owner/menu',
  );
  return data;
}

export async function updateOwnerMenuItem(
  productId: string,
  payload: OwnerMenuUpdatePayload,
): Promise<FranchiseProductAssignment> {
  const { data } = await api.patch<FranchiseProductAssignment>(
    `/owner/menu/${productId}`,
    payload,
  );
  return data;
}
