import type { UserRole } from './auth';

export type ManagedUser = {
  id: string;
  full_name: string;
  email: string | null;
  login_id?: string | null;
  phone: string | null;
  role: UserRole;
  franchise_id: string | null;
  franchise_name: string | null;
  is_active: boolean;
  is_logged_in?: boolean | null;
  created_at: string | null;
  updated_at: string | null;
};

export type UserListResponse = {
  items: ManagedUser[];
  total: number;
};

export type EmployeeListResponse = UserListResponse & {
  active_count: number;
  employee_limit: number;
};

export type UserCreatePayload = {
  full_name: string;
  email: string;
  phone?: string | null;
  role: UserRole;
  franchise_id?: string | null;
};

export type UserUpdatePayload = {
  full_name?: string;
  phone?: string | null;
  is_active?: boolean;
  franchise_id?: string | null;
};

export type EmployeeCreatePayload = {
  full_name: string;
  login_id: string;
  password: string;
  confirm_password: string;
  phone?: string | null;
};

export type EmployeeUpdatePayload = {
  full_name?: string;
  login_id?: string;
  phone?: string | null;
  is_active?: boolean;
};

export type UserCreateResponse = {
  user: ManagedUser;
  password_setup: string;
  message: string;
};

export type PasswordResetResponse = {
  password_setup: string;
  message: string;
};

export type EmployeeSessionStatus = 'ACTIVE' | 'COMPLETED';

export type EmployeeSession = {
  id: string;
  employee_id: string;
  employee_name_snapshot: string;
  login_at: string;
  logout_at: string | null;
  status: EmployeeSessionStatus;
  created_at?: string | null;
};

export type EmployeeSessionListResponse = {
  employee_id: string;
  employee_name: string;
  login_id?: string | null;
  items: EmployeeSession[];
};
