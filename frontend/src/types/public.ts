export type PublicCategory = {
  id: string;
  name: string;
  display_order: number;
};

export type PublicProduct = {
  id: string;
  category_id: string;
  category_name: string;
  name: string;
  description: string | null;
  image_url: string | null;
};

export type PublicGalleryItem = {
  id: string;
  title: string | null;
  caption: string | null;
  author_name: string | null;
  media_type: 'IMAGE' | 'VIDEO' | 'TESTIMONIAL';
  media_url: string | null;
  display_order: number;
};

export type AdminGalleryItem = PublicGalleryItem & {
  is_approved: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
};
