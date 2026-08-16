import { api } from './api';
import type { AuditCreatePayload, AuditDetail, AuditListParams, AuditListResponse } from '../types/audit';

export async function listAudits(params: AuditListParams = {}): Promise<AuditListResponse> {
  const { data } = await api.get<AuditListResponse>('/audits', {
    params: {
      franchise_id: params.franchise_id || undefined,
      from_date: params.from_date || undefined,
      to_date: params.to_date || undefined,
      overall_status: params.overall_status || undefined,
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
    },
  });
  return data;
}

export async function getAudit(auditId: string): Promise<AuditDetail> {
  const { data } = await api.get<AuditDetail>(`/audits/${auditId}`);
  return data;
}

export async function createAudit(payload: AuditCreatePayload): Promise<AuditDetail> {
  const { data } = await api.post<AuditDetail>('/audits', payload);
  return data;
}
