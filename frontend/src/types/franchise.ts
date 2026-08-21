export type FranchiseStatus =
  | 'APPLICATION'
  | 'PENDING_PAYMENT'
  | 'SETUP'
  | 'ACTIVE'
  | 'SUSPENDED'
  | 'CLOSED';

export const FRANCHISE_STATUSES: FranchiseStatus[] = [
  'APPLICATION',
  'PENDING_PAYMENT',
  'SETUP',
  'ACTIVE',
  'SUSPENDED',
  'CLOSED',
];

export const FRANCHISE_TIERS = ['Founder', 'Growth', 'Scale', 'Elite'] as const;
export type FranchiseTier = (typeof FRANCHISE_TIERS)[number];

export type FranchiseOwner = {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
};

export type FranchiseApplication = {
  id: string;
  applicant_name: string;
  email: string;
  phone: string | null;
  city: string | null;
  state: string | null;
  investment_range: string | null;
  message: string | null;
  status: string;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  converted_franchise_id?: string | null;
};

export type FranchisePayment = {
  id: string;
  amount: number;
  currency: string;
  payment_method: string | null;
  reference_number: string | null;
  status: string;
  paid_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type FranchisePaymentMethod = 'CASH' | 'BANK_TRANSFER' | 'UPI' | 'CHEQUE' | 'OTHER';

export type FranchiseOfflinePaymentPayload = {
  amount: number;
  paid_at: string;
  payment_method: FranchisePaymentMethod;
  reference_number?: string | null;
  notes?: string | null;
};

export type LaunchChecklistItem = {
  id: string;
  item_key: string;
  item_name: string;
  display_order: number;
  is_completed: boolean;
  completed_at: string | null;
  completed_by: string | null;
  created_at: string;
  updated_at: string;
};

export type Franchise = {
  id: string;
  name: string;
  code: string | null;
  owner_email: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  tier: string | null;
  status: FranchiseStatus;
  open_date: string | null;
  closed_at: string | null;
  employee_limit: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  owner: FranchiseOwner | null;
  payment_status: string | null;
  launch_progress_completed: number;
  launch_progress_total: number;
};

export type FranchiseDetail = Franchise & {
  settings: Record<string, unknown>;
  applications: FranchiseApplication[];
  payments: FranchisePayment[];
  launch_checklist: LaunchChecklistItem[];
};

export type FranchiseListResponse = {
  items: Franchise[];
  total: number;
};

export type FranchiseWritePayload = {
  name: string;
  code?: string | null;
  owner_email?: string | null;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  tier: FranchiseTier;
  status?: FranchiseStatus;
  open_date?: string | null;
  employee_limit?: number;
};
