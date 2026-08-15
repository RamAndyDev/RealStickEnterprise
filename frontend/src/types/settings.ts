export type GstSettings = {
  id: string;
  rate: number;
  cgst_rate: number;
  sgst_rate: number;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export type OfferDiscountType = 'PERCENTAGE';

export type Offer = {
  id: string;
  name: string;
  description: string | null;
  discount_type: OfferDiscountType;
  discount_value: number;
  is_active: boolean;
  valid_from: string | null;
  valid_to: string | null;
  franchise_id: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type OfferListResponse = {
  items: Offer[];
  total: number;
};

export type OfferWritePayload = {
  name: string;
  description?: string | null;
  discount_type?: OfferDiscountType;
  discount_value: number;
  is_active: boolean;
  valid_from?: string | null;
  valid_to?: string | null;
};
