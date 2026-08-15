import { api } from './api';
import type {
  PosMenuResponse,
  PosOfferListResponse,
  PosOrder,
  PosOrderCreatePayload,
} from '../types/pos';

export async function fetchPosMenu(): Promise<PosMenuResponse> {
  const { data } = await api.get<PosMenuResponse>('/pos/menu');
  return data;
}

export async function fetchPosOffers(): Promise<PosOfferListResponse> {
  const { data } = await api.get<PosOfferListResponse>('/pos/offers');
  return data;
}

export async function completePosOrder(payload: PosOrderCreatePayload): Promise<PosOrder> {
  const { data } = await api.post<PosOrder>('/pos/orders', payload);
  return data;
}

export async function fetchPosOrder(orderId: string): Promise<PosOrder> {
  const { data } = await api.get<PosOrder>(`/pos/orders/${orderId}`);
  return data;
}
