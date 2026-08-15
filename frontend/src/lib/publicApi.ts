import type { AdminGalleryItem, PublicCategory, PublicGalleryItem, PublicProduct } from '../types/public';
import { api } from './api';

export async function fetchPublicCategories(): Promise<{ items: PublicCategory[]; total: number }> {
  const { data } = await api.get<{ items: PublicCategory[]; total: number }>('/public/categories');
  return data;
}

export async function fetchPublicProducts(): Promise<{ items: PublicProduct[]; total: number }> {
  const { data } = await api.get<{ items: PublicProduct[]; total: number }>('/public/products');
  return data;
}

export async function fetchPublicGallery(): Promise<{ items: PublicGalleryItem[]; total: number }> {
  const { data } = await api.get<{ items: PublicGalleryItem[]; total: number }>('/public/gallery');
  return data;
}

export async function submitContactEnquiry(payload: {
  name: string;
  phone: string;
  email: string;
  message: string;
  website?: string;
}): Promise<{ message: string }> {
  const { data } = await api.post<{ message: string }>('/public/contact', payload);
  return data;
}

export async function listAdminGallery(): Promise<{ items: AdminGalleryItem[]; total: number }> {
  const { data } = await api.get<{ items: AdminGalleryItem[]; total: number }>('/admin/gallery');
  return data;
}

export async function createAdminGalleryItem(payload: {
  media_type: AdminGalleryItem['media_type'];
  title?: string;
  caption?: string;
  author_name?: string;
  media_url?: string;
  display_order?: number;
  is_approved?: boolean;
}): Promise<AdminGalleryItem> {
  const { data } = await api.post<AdminGalleryItem>('/admin/gallery', payload);
  return data;
}

export async function updateAdminGalleryItem(
  id: string,
  payload: Partial<{
    title: string | null;
    caption: string | null;
    author_name: string | null;
    media_url: string | null;
    display_order: number;
    is_approved: boolean;
    is_archived: boolean;
  }>,
): Promise<AdminGalleryItem> {
  const { data } = await api.patch<AdminGalleryItem>(`/admin/gallery/${id}`, payload);
  return data;
}

export async function uploadAdminGalleryMedia(id: string, file: File): Promise<AdminGalleryItem> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<AdminGalleryItem>(`/admin/gallery/${id}/media`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}
