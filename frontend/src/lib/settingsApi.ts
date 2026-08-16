import { api } from './api';
import type {
  GstSettings,
  Offer,
  OfferListResponse,
  OfferWritePayload,
  Promotion,
  PromotionListResponse,
  PromotionWritePayload,
} from '../types/settings';

export async function fetchGstSettings(): Promise<GstSettings> {
  const { data } = await api.get<GstSettings>('/admin/gst');
  return data;
}

export async function updateGstSettings(rate: number): Promise<GstSettings> {
  const { data } = await api.patch<GstSettings>('/admin/gst', { rate });
  return data;
}

export async function listOwnerOffers(): Promise<OfferListResponse> {
  const { data } = await api.get<OfferListResponse>('/owner/offers');
  return data;
}

export async function createOwnerOffer(payload: OfferWritePayload): Promise<Offer> {
  const { data } = await api.post<Offer>('/owner/offers', payload);
  return data;
}

export async function updateOwnerOffer(id: string, payload: Partial<OfferWritePayload>): Promise<Offer> {
  const { data } = await api.patch<Offer>(`/owner/offers/${id}`, payload);
  return data;
}

export async function listOwnerPromotions(): Promise<PromotionListResponse> {
  const { data } = await api.get<PromotionListResponse>('/owner/promotions');
  return data;
}

export async function listPromotions(): Promise<PromotionListResponse> {
  const { data } = await api.get<PromotionListResponse>('/admin/promotions');
  return data;
}

export async function createPromotion(payload: PromotionWritePayload): Promise<Promotion> {
  const { data } = await api.post<Promotion>('/admin/promotions', payload);
  return data;
}

export async function updatePromotion(
  id: string,
  payload: Partial<PromotionWritePayload>,
): Promise<Promotion> {
  const { data } = await api.patch<Promotion>(`/admin/promotions/${id}`, payload);
  return data;
}
