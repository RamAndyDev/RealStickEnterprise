import { api } from './api';
import type { BillListParams, BillListResponse, CompletedBill } from '../types/orders';

export async function fetchCompletedOrders(params: BillListParams = {}): Promise<BillListResponse> {
  const { data } = await api.get<BillListResponse>('/orders', {
    params: {
      franchise_id: params.franchise_id || undefined,
      bill_number: params.bill_number || undefined,
      payment_method: params.payment_method || undefined,
      from_date: params.from_date || undefined,
      to_date: params.to_date || undefined,
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
    },
  });
  return data;
}

export async function fetchCompletedOrder(orderId: string): Promise<CompletedBill> {
  const { data } = await api.get<CompletedBill>(`/orders/${orderId}`);
  return data;
}
