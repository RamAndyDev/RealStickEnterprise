import type { Product } from '../../types/product';
import { productImageUrl } from '../../types/product';

type Size = 'sm' | 'md' | 'lg' | 'auto';

const sizeClass: Record<Size, string> = {
  sm: 'h-10 w-10',
  md: 'h-14 w-14',
  lg: 'h-28 w-28',
  auto: '',
};

export function ProductImage({
  product,
  src,
  alt,
  size = 'md',
  className = '',
}: {
  product?: Pick<Product, 'image_url' | 'metadata' | 'name'> | null;
  src?: string | null;
  alt?: string;
  size?: Size;
  className?: string;
}) {
  const url = src ?? (product ? productImageUrl(product) : null);
  const label = alt ?? product?.name ?? 'Product';

  if (url) {
    return (
      <img
        src={url}
        alt={label}
        className={`${sizeClass[size]} shrink-0 object-cover ${
          size === 'auto' ? '' : 'rounded-lg'
        } ${className}`}
      />
    );
  }

  return (
    <div
      className={`${sizeClass[size]} flex shrink-0 items-center justify-center rounded-lg bg-[#F3F1EB] text-[#8A8A84] ${className}`}
      aria-label={`${label} placeholder`}
    >
      <svg
        viewBox="0 0 24 24"
        className={size === 'lg' ? 'h-10 w-10' : size === 'md' ? 'h-6 w-6' : 'h-5 w-5'}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        aria-hidden
      >
        <rect x="3" y="5" width="18" height="14" rx="2" />
        <circle cx="8.5" cy="10" r="1.5" />
        <path d="M21 16l-5.5-5.5L7 19" />
      </svg>
    </div>
  );
}
