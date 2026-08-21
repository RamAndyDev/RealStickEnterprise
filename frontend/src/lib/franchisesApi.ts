import type {
  FranchiseDetail,
  FranchiseListResponse,
  FranchiseOfflinePaymentPayload,
  FranchiseStatus,
  FranchiseWritePayload,
  LaunchChecklistItem,
  FranchiseApplication,
} from '../types/franchise';
import { api } from './api';

export type FranchiseListParams = {
  status?: FranchiseStatus | '';
  search?: string;
  include_archived?: boolean;
};

export async function listFranchises(params: FranchiseListParams = {}): Promise<FranchiseListResponse> {
  const { data } = await api.get<FranchiseListResponse>('/admin/franchises', {
    params: {
      status: params.status || undefined,
      search: params.search || undefined,
      include_archived: params.include_archived || undefined,
    },
  });
  return data;
}

export async function getFranchise(id: string): Promise<FranchiseDetail> {
  const { data } = await api.get<FranchiseDetail>(`/admin/franchises/${id}`);
  return data;
}

export async function createFranchise(payload: FranchiseWritePayload): Promise<FranchiseDetail> {
  const { data } = await api.post<FranchiseDetail>('/admin/franchises', payload);
  return data;
}

export async function updateFranchise(
  id: string,
  payload: Partial<FranchiseWritePayload> & { is_archived?: boolean },
): Promise<FranchiseDetail> {
  const { data } = await api.patch<FranchiseDetail>(`/admin/franchises/${id}`, payload);
  return data;
}

export async function updateFranchiseStatus(
  id: string,
  status: FranchiseStatus,
): Promise<FranchiseDetail> {
  const { data } = await api.patch<FranchiseDetail>(`/admin/franchises/${id}/status`, { status });
  return data;
}

export async function assignFranchiseOwner(
  id: string,
  body: { owner_profile_id?: string; owner_email?: string },
): Promise<FranchiseDetail> {
  const { data } = await api.patch<FranchiseDetail>(`/admin/franchises/${id}/owner`, body);
  return data;
}

export type FranchiseOwnerCreateResponse = {
  franchise: FranchiseDetail;
  owner: {
    id: string;
    full_name: string;
    email: string | null;
    phone: string | null;
    is_active: boolean;
  };
  password_setup: string;
  message: string;
};

export async function createFranchiseOwner(
  id: string,
  body: { full_name: string; email: string; phone?: string | null },
): Promise<FranchiseOwnerCreateResponse> {
  const { data } = await api.post<FranchiseOwnerCreateResponse>(
    `/admin/franchises/${id}/owners`,
    body,
  );
  return data;
}

export async function recordOfflineFranchisePayment(
  id: string,
  payload: FranchiseOfflinePaymentPayload,
): Promise<FranchiseDetail> {
  const { data } = await api.post<FranchiseDetail>(`/admin/franchises/${id}/payments`, payload);
  return data;
}

export async function getLaunchChecklist(id: string): Promise<LaunchChecklistItem[]> {
  const { data } = await api.get<LaunchChecklistItem[]>(`/admin/franchises/${id}/launch-checklist`);
  return data;
}

export async function updateLaunchChecklistItem(
  franchiseId: string,
  itemId: string,
  is_completed: boolean,
): Promise<LaunchChecklistItem> {
  const { data } = await api.patch<LaunchChecklistItem>(
    `/admin/franchises/${franchiseId}/launch-checklist/${itemId}`,
    { is_completed },
  );
  return data;
}

export async function listFranchiseApplications(params: {
  status?: string;
  search?: string;
} = {}): Promise<{ items: FranchiseApplication[]; total: number }> {
  const { data } = await api.get<{ items: FranchiseApplication[]; total: number }>(
    '/admin/franchise-applications',
    { params },
  );
  return data;
}
