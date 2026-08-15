"""In-memory equivalent of public.set_product_category_active (used by FakeDatabase tests)."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


class CategoryOpsError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def set_product_category_active_atomic(
    tables: dict[str, list[dict[str, Any]]],
    category_id: object,
    is_active: bool,
) -> dict[str, Any]:
    categories = tables.setdefault('product_categories', [])
    products = tables.setdefault('products', [])
    snapshot_categories = deepcopy(categories)
    snapshot_products = deepcopy(products)

    try:
        category = next(
            (row for row in categories if str(row.get('id')) == str(category_id)),
            None,
        )
        if not category:
            raise CategoryOpsError('NOT_FOUND', 'Category not found')

        category['is_active'] = bool(is_active)
        category['updated_at'] = _now()

        if not is_active:
            for product in products:
                if str(product.get('category_id')) == str(category_id):
                    product['is_active'] = False
                    product['updated_at'] = _now()

        return deepcopy(category)
    except Exception:
        categories[:] = snapshot_categories
        products[:] = snapshot_products
        raise
