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
  promotion_id?: string | null;
  promotion_name?: string | null;
  promotion_promo_code?: string | null;
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
  promotion_id?: string | null;
  clear_promotion_id?: boolean;
};

export type Promotion = {
  id: string;
  name: string;
  description: string | null;
  promo_code: string;
  valid_from: string | null;
  valid_to: string | null;
  is_active: boolean;
  franchise_ids: string[];
  created_at?: string | null;
  updated_at?: string | null;
};

export type PromotionListResponse = {
  items: Promotion[];
  total: number;
};

export type PromotionWritePayload = {
  name: string;
  description?: string | null;
  promo_code: string;
  is_active: boolean;
  valid_from?: string | null;
  valid_to?: string | null;
  franchise_ids: string[];
};
