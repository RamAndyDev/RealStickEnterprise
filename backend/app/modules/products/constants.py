"""Initial RealStick product categories (seed reference only — not an allow-list)."""

from __future__ import annotations

# Seeded by supabase/migrations/0002_seed_fixed_product_categories.sql.
# The live source of truth is product_categories; admins may add more.
INITIAL_PRODUCT_CATEGORIES: tuple[str, ...] = (
    'Zest Collection',
    'Garden Collection',
    'Harvest Collection',
    'The Reserve',
    'Kulfi Heritage',
)

INITIAL_CATEGORY_DISPLAY_ORDER: dict[str, int] = {
    'Zest Collection': 1,
    'Garden Collection': 2,
    'Harvest Collection': 3,
    'The Reserve': 4,
    'Kulfi Heritage': 5,
}

# Back-compat aliases for migration tests / older imports.
FIXED_PRODUCT_CATEGORIES = INITIAL_PRODUCT_CATEGORIES
FIXED_CATEGORY_DISPLAY_ORDER = INITIAL_CATEGORY_DISPLAY_ORDER

PRODUCT_IMAGE_BUCKET = 'product-images'
PRODUCT_IMAGE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_CONTENT_TYPES: frozenset[str] = frozenset(
    {'image/jpeg', 'image/png', 'image/webp'}
)
ALLOWED_IMAGE_EXTENSIONS: dict[str, str] = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
}

# Safe product delete: hard-delete only when no business/historical references exist.
PRODUCT_DELETE_BLOCKED_DETAIL = (
    'This product cannot be deleted because it is already used in existing business records. '
    'Deactivate it instead.'
)
