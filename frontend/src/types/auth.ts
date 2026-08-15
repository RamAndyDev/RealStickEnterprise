export type UserRole = 'SYSTEM_ADMIN' | 'FRANCHISE_OWNER' | 'EMPLOYEE';

export type AuthProfile = {
  id: string;
  email: string | null;
  full_name: string;
  role: UserRole;
  franchise_id: string | null;
  franchise_name?: string | null;
  phone?: string | null;
  is_active: boolean;
  created_at?: string | null;
};
