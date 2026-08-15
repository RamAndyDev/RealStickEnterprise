import type {
  EmployeeCreatePayload,
  EmployeeListResponse,
  EmployeeUpdatePayload,
  ManagedUser,
  PasswordResetResponse,
  UserCreatePayload,
  UserCreateResponse,
  UserListResponse,
  UserUpdatePayload,
} from '../types/user';
import type { UserRole } from '../types/auth';
import { api } from './api';

export type AdminUserListParams = {
  role?: UserRole | '';
  franchise_id?: string;
  is_active?: boolean;
  search?: string;
};

export async function listAdminUsers(params: AdminUserListParams = {}): Promise<UserListResponse> {
  const { data } = await api.get<UserListResponse>('/admin/users', {
    params: {
      role: params.role || undefined,
      franchise_id: params.franchise_id || undefined,
      is_active: params.is_active,
      search: params.search || undefined,
    },
  });
  return data;
}

export async function getAdminUser(id: string): Promise<ManagedUser> {
  const { data } = await api.get<ManagedUser>(`/admin/users/${id}`);
  return data;
}

export async function createAdminUser(payload: UserCreatePayload): Promise<UserCreateResponse> {
  const { data } = await api.post<UserCreateResponse>('/admin/users', payload);
  return data;
}

export async function updateAdminUser(id: string, payload: UserUpdatePayload): Promise<ManagedUser> {
  const { data } = await api.patch<ManagedUser>(`/admin/users/${id}`, payload);
  return data;
}

export async function resetAdminUserPassword(id: string): Promise<PasswordResetResponse> {
  const { data } = await api.post<PasswordResetResponse>(`/admin/users/${id}/reset-password`);
  return data;
}

export async function listEmployees(): Promise<EmployeeListResponse> {
  const { data } = await api.get<EmployeeListResponse>('/owner/employees');
  return data;
}

export async function getEmployee(id: string): Promise<ManagedUser> {
  const { data } = await api.get<ManagedUser>(`/owner/employees/${id}`);
  return data;
}

export async function createEmployee(payload: EmployeeCreatePayload): Promise<UserCreateResponse> {
  const { data } = await api.post<UserCreateResponse>('/owner/employees', payload);
  return data;
}

export async function updateEmployee(id: string, payload: EmployeeUpdatePayload): Promise<ManagedUser> {
  const { data } = await api.patch<ManagedUser>(`/owner/employees/${id}`, payload);
  return data;
}

export async function resetEmployeePassword(id: string): Promise<PasswordResetResponse> {
  const { data } = await api.post<PasswordResetResponse>(`/owner/employees/${id}/reset-password`);
  return data;
}

export async function changeOwnPassword(new_password: string): Promise<{ message: string }> {
  const { data } = await api.post<{ message: string }>('/auth/change-password', { new_password });
  return data;
}
