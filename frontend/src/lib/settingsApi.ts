import { api } from './api';
import type { GstSettings, Offer, OfferListResponse, OfferWritePayload } from '../types/settings';

export async function fetchGstSettings(): Promise<GstSettings> {
  const { data } = await api.get<GstSettings>('/admin/gst');
  return data;
}

export async function updateGstSettings(rate: number): Promise<GstSettings> {
  const { data } = await api.patch<GstSettings>('/admin/gst', { rate });
  return data;
}

export async function listOffers(): Promise<OfferListResponse> {
  const { data } = await api.get<OfferListResponse>('/admin/offers');
  return data;
}

export async function createOffer(payload: OfferWritePayload): Promise<Offer> {
  const { data } = await api.post<Offer>('/admin/offers', payload);
  return data;
}

export async function updateOffer(id: string, payload: Partial<OfferWritePayload>): Promise<Offer> {
  const { data } = await api.patch<Offer>(`/admin/offers/${id}`, payload);
  return data;
}
