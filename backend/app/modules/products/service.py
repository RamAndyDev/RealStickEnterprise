from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, UploadFile, status

from app.core.security import CurrentProfile
from app.modules.products.images import (
    build_product_image_path,
    image_metadata,
    read_and_validate_image,
    strip_image_metadata,
)
from app.modules.products.pricing import (
    MASTER_PRICE_CONFLICT,
    assert_owner_may_edit_selling_price,
    owner_can_edit_selling_price,
    selling_price_conflicts_with_master,
    validate_selling_price,
)
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import (
    FranchiseProductAssign,
    FranchiseProductAssignment,
    FranchiseProductListResponse,
    FranchiseProductUpdate,
    OwnerFranchiseProductUpdate,
    Product,
    ProductCategory,
    ProductCategoryCreate,
    ProductCategoryListResponse,
    ProductCategorySummary,
    ProductCategoryUpdate,
    ProductCreate,
    ProductListResponse,
    ProductUpdate,
)

logger = logging.getLogger(__name__)


def _money(value: object) -> float:
    return float(Decimal(str(value)))


def _serialize_decimal(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _resolve_image_url(row: dict) -> str | None:
    meta = row.get('metadata') or {}
    if isinstance(meta, dict):
        url = meta.get('image_url')
        if isinstance(url, str) and url.strip():
            return url.strip()
    column = row.get('image_url')
    if isinstance(column, str) and column.strip():
        return column.strip()
    return None


class ProductService:
    def __init__(self, repo: ProductRepository | None = None) -> None:
        self.repo = repo or ProductRepository()

    # ── Categories (dynamic; DB is source of truth) ─────────────────────────

    def list_categories(self, *, include_inactive: bool = True) -> ProductCategoryListResponse:
        rows = self.repo.list_categories(include_inactive=include_inactive)
        items = [ProductCategory.model_validate(row) for row in rows]
        return ProductCategoryListResponse(items=items, total=len(items))

    def create_category(self, data: ProductCategoryCreate) -> ProductCategory:
        conflict = self.repo.find_category_by_name_ci(data.name)
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Category name already exists',
            )
        try:
            created = self.repo.create_category(
                {
                    'name': data.name,
                    'display_order': data.display_order,
                    'is_active': data.is_active,
                }
            )
        except Exception as exc:
            if self.repo.is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Category name already exists',
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to create category',
            ) from exc
        return ProductCategory.model_validate(created)

    def update_category(self, category_id: UUID, data: ProductCategoryUpdate) -> ProductCategory:
        existing = self.repo.get_category(category_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return ProductCategory.model_validate(existing)

        if 'name' in updates and updates['name']:
            conflict = self.repo.find_category_by_name_ci(updates['name'])
            if conflict and str(conflict['id']) != str(category_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Category name already exists',
                )

        is_active = updates.pop('is_active', None)
        updated = existing

        if is_active is not None:
            try:
                updated = self.repo.set_category_active(category_id, bool(is_active))
            except Exception as exc:
                if str(exc) == 'CATEGORY_NOT_FOUND' or 'not found' in str(exc).lower():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail='Category not found',
                    ) from exc
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail='Unable to update category',
                ) from exc

        if not updates:
            return ProductCategory.model_validate(updated)

        try:
            updated = self.repo.update_category(category_id, updates)
        except Exception as exc:
            if self.repo.is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Category name already exists',
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to update category',
            ) from exc
        return ProductCategory.model_validate(updated)

    def delete_category(self, category_id: UUID) -> None:
        existing = self.repo.get_category(category_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')

        product_count = self.repo.count_products_for_category(category_id)
        if product_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    'Category is referenced by products and cannot be deleted. '
                    'Deactivate it instead.'
                ),
            )

        try:
            deleted = self.repo.delete_category(category_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to delete category',
            ) from exc
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')

    def _require_category(
        self,
        category_id: UUID,
        *,
        require_active: bool,
    ) -> dict:
        category = self.repo.get_category(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Category not found',
            )
        if require_active and not category.get('is_active', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Category is inactive and cannot be assigned to a product',
            )
        return category

    # ── Products ────────────────────────────────────────────────────────────

    def list_products(
        self,
        *,
        category_id: UUID | None = None,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> ProductListResponse:
        rows = self.repo.list_products(
            category_id=category_id,
            search=search,
            is_active=is_active,
        )
        categories = {
            str(c['id']): c for c in self.repo.list_categories(include_inactive=True)
        }
        items = [self._to_product(row, categories.get(str(row.get('category_id')))) for row in rows]
        return ProductListResponse(items=items, total=len(items))

    def get_product(self, product_id: UUID) -> Product:
        row = self.repo.get_product(product_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found')
        category = None
        if row.get('category_id'):
            category = self.repo.get_category(UUID(str(row['category_id'])))
        return self._to_product(row, category)

    def create_product(self, data: ProductCreate) -> Product:
        category = self._require_category(data.category_id, require_active=True)

        payload = {
            'name': data.name,
            'category_id': str(data.category_id),
            'description': data.description,
            'image_url': None,
            'price': float(data.price),
            'sku': data.sku,
            'min_price': _serialize_decimal(data.min_price),
            'max_price': _serialize_decimal(data.max_price),
            'is_active': data.is_active,
            'metadata': data.metadata or {},
        }

        try:
            created = self.repo.create_product(payload)
        except Exception as exc:
            if self.repo.is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Product SKU already exists',
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to create product',
            ) from exc

        return self._to_product(created, category)

    def update_product(self, product_id: UUID, data: ProductUpdate) -> Product:
        existing = self.repo.get_product(product_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found')

        updates = data.model_dump(exclude_unset=True)

        if 'metadata' in updates and updates['metadata'] is not None:
            # Preserve existing image keys; client cannot overwrite via PATCH body.
            meta = strip_image_metadata(updates['metadata'])
            existing_meta = existing.get('metadata') or {}
            if isinstance(existing_meta, dict):
                if existing_meta.get('image_url'):
                    meta['image_url'] = existing_meta['image_url']
                if existing_meta.get('image_path'):
                    meta['image_path'] = existing_meta['image_path']
            updates['metadata'] = meta

        if 'category_id' in updates and updates['category_id'] is not None:
            new_category_id = UUID(str(updates['category_id']))
            current_category_id = existing.get('category_id')
            # Re-assignment requires an active category; keeping the same category is allowed
            # even if that category later became inactive.
            changing = (
                current_category_id is None
                or str(current_category_id) != str(new_category_id)
            )
            category = self._require_category(new_category_id, require_active=changing)
            updates['category_id'] = str(category['id'])

        for key in ('price', 'min_price', 'max_price'):
            if key in updates and updates[key] is not None:
                updates[key] = float(updates[key])

        if 'price' in updates and updates['price'] is not None:
            selling_prices = [
                row['selling_price']
                for row in self.repo.list_franchise_prices_for_product(product_id, active_only=True)
            ]
            if selling_price_conflicts_with_master(selling_prices, updates['price']):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=MASTER_PRICE_CONFLICT,
                )

        if not updates:
            return self.get_product(product_id)

        try:
            self.repo.update_product(product_id, updates)
        except Exception as exc:
            if MASTER_PRICE_CONFLICT.split('.')[0].lower() in str(exc).lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=MASTER_PRICE_CONFLICT,
                ) from exc
            if self.repo.is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Product SKU already exists',
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to update product',
            ) from exc

        return self.get_product(product_id)

    # ── Product images ──────────────────────────────────────────────────────

    async def upload_product_image(self, product_id: UUID, file: UploadFile) -> Product:
        existing = self.repo.get_product(product_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found')

        content, content_type, extension = await read_and_validate_image(file)
        path = build_product_image_path(str(product_id), extension)

        # Remove previous storage object if present.
        old_meta = existing.get('metadata') or {}
        old_path = old_meta.get('image_path') if isinstance(old_meta, dict) else None

        try:
            public_url = self.repo.upload_product_image(
                path=path,
                content=content,
                content_type=content_type,
            )
        except Exception as exc:
            logger.exception('Product image storage upload failed')
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to upload product image',
            ) from exc

        meta = dict(old_meta) if isinstance(old_meta, dict) else {}
        meta.pop('emoji', None)
        meta.update(image_metadata(public_url, path))

        try:
            self.repo.update_product(
                product_id,
                {
                    'metadata': meta,
                    'image_url': public_url,
                },
            )
        except Exception as exc:
            # Best-effort cleanup of newly uploaded object
            try:
                self.repo.remove_product_image(path)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to save product image metadata',
            ) from exc

        if old_path and old_path != path:
            try:
                self.repo.remove_product_image(str(old_path))
            except Exception:
                pass

        return self.get_product(product_id)

    def remove_product_image(self, product_id: UUID) -> Product:
        existing = self.repo.get_product(product_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found')

        meta = dict(existing.get('metadata') or {})
        path = meta.get('image_path')
        cleaned = strip_image_metadata(meta)

        try:
            self.repo.update_product(
                product_id,
                {
                    'metadata': cleaned,
                    'image_url': None,
                },
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to remove product image',
            ) from exc

        if path:
            try:
                self.repo.remove_product_image(str(path))
            except Exception:
                pass

        return self.get_product(product_id)

    # ── Franchise assignments ───────────────────────────────────────────────

    def list_franchise_products(self, franchise_id: UUID) -> FranchiseProductListResponse:
        self._require_franchise(franchise_id)
        assignments = self.repo.list_franchise_products(franchise_id)
        product_ids = [str(a['product_id']) for a in assignments]
        products = {str(p['id']): p for p in self.repo.get_products_by_ids(product_ids)}
        categories = {
            str(c['id']): c for c in self.repo.list_categories(include_inactive=True)
        }

        items = [
            self._to_assignment(row, products.get(str(row['product_id'])), categories)
            for row in assignments
        ]
        return FranchiseProductListResponse(items=items, total=len(items))

    def assign_franchise_product(
        self,
        franchise_id: UUID,
        data: FranchiseProductAssign,
    ) -> FranchiseProductAssignment:
        self._require_franchise(franchise_id)
        product = self.repo.get_product(data.product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Product not found')

        validate_selling_price(data.selling_price, product['price'])

        existing = self.repo.get_franchise_product(franchise_id, data.product_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Product is already assigned to this franchise',
            )

        payload = {
            'franchise_id': str(franchise_id),
            'product_id': str(data.product_id),
            'selling_price': float(data.selling_price),
            'is_active': data.is_active,
        }

        try:
            created = self.repo.create_franchise_product(payload)
        except Exception as exc:
            if self.repo.is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Product is already assigned to this franchise',
                ) from exc
            if 'selling price' in str(exc).lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to assign product to franchise',
            ) from exc

        categories = {str(c['id']): c for c in self.repo.list_categories(include_inactive=True)}
        return self._to_assignment(created, product, categories)

    def update_franchise_product(
        self,
        franchise_id: UUID,
        product_id: UUID,
        data: FranchiseProductUpdate,
    ) -> FranchiseProductAssignment:
        self._require_franchise(franchise_id)
        existing = self.repo.get_franchise_product(franchise_id, product_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Franchise product assignment not found',
            )

        updates = data.model_dump(exclude_unset=True)
        if 'selling_price' in updates and updates['selling_price'] is not None:
            product = self.repo.get_product(product_id)
            if not product:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Product not found')
            validate_selling_price(updates['selling_price'], product['price'])
            updates['selling_price'] = float(updates['selling_price'])

        try:
            updated = self.repo.update_franchise_product(franchise_id, product_id, updates)
        except Exception as exc:
            if 'selling price' in str(exc).lower() or 'master price' in str(exc).lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to update franchise product pricing',
            ) from exc

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Franchise product assignment not found',
            )

        product = self.repo.get_product(product_id)
        categories = {str(c['id']): c for c in self.repo.list_categories(include_inactive=True)}
        return self._to_assignment(updated, product, categories)

    def list_owner_menu(self, owner: CurrentProfile) -> FranchiseProductListResponse:
        franchise_id = self._owner_franchise_id(owner)
        return self.list_franchise_products(franchise_id)

    def update_owner_menu_item(
        self,
        owner: CurrentProfile,
        product_id: UUID,
        data: OwnerFranchiseProductUpdate,
    ) -> FranchiseProductAssignment:
        franchise_id = self._owner_franchise_id(owner)
        existing = self.repo.get_franchise_product(franchise_id, product_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Access to this franchise product is not allowed',
            )
        product = self.repo.get_product(product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found')
        assert_owner_may_edit_selling_price(product, existing)
        return self.update_franchise_product(
            franchise_id,
            product_id,
            FranchiseProductUpdate(selling_price=data.selling_price),
        )

    def _owner_franchise_id(self, owner: CurrentProfile) -> UUID:
        if owner.franchise_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Franchise owner profile must belong to a franchise',
            )
        return owner.franchise_id

    def _require_franchise(self, franchise_id: UUID) -> dict:
        franchise = self.repo.get_franchise(franchise_id)
        if not franchise:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')
        return franchise

    def _to_product(self, row: dict, category: dict | None) -> Product:
        category_summary = None
        if category:
            category_summary = ProductCategorySummary(
                id=category['id'],
                name=category['name'],
                display_order=category.get('display_order') or 0,
                is_active=bool(category.get('is_active', True)),
            )
        return Product(
            id=row['id'],
            category_id=row.get('category_id'),
            sku=row.get('sku'),
            name=row['name'],
            description=row.get('description'),
            image_url=_resolve_image_url(row),
            price=_money(row['price']),
            min_price=_money(row['min_price']) if row.get('min_price') is not None else None,
            max_price=_money(row['max_price']) if row.get('max_price') is not None else None,
            is_active=bool(row.get('is_active', True)),
            metadata=row.get('metadata') or {},
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            category=category_summary,
        )

    def _to_assignment(
        self,
        row: dict,
        product: dict | None,
        categories: dict[str, dict],
    ) -> FranchiseProductAssignment:
        category_id = None
        category_name = None
        product_name = None
        product_description = None
        product_is_active = None
        master_price = None
        image_url = None
        category_is_active = None

        if product:
            product_name = product.get('name')
            product_description = product.get('description')
            product_is_active = bool(product.get('is_active', True))
            master_price = _money(product['price']) if product.get('price') is not None else None
            category_id = product.get('category_id')
            if category_id and str(category_id) in categories:
                category_row = categories[str(category_id)]
                category_name = category_row.get('name')
                category_is_active = bool(category_row.get('is_active', True))
            elif category_id:
                category_is_active = False
            else:
                category_is_active = True
            image_url = _resolve_image_url(product)

        assignment_active = bool(row.get('is_active', True))
        available = bool(product_is_active) and assignment_active and bool(category_is_active)
        price_editable = owner_can_edit_selling_price(
            {'is_active': product_is_active},
            {'is_active': assignment_active},
        )

        return FranchiseProductAssignment(
            id=row['id'],
            franchise_id=row['franchise_id'],
            product_id=row['product_id'],
            selling_price=_money(row['selling_price']),
            is_active=assignment_active,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            product_name=product_name,
            product_description=product_description,
            product_is_active=product_is_active,
            master_price=master_price,
            category_id=category_id,
            category_name=category_name,
            image_url=image_url,
            category_is_active=category_is_active,
            available_for_pos=available,
            price_editable=price_editable,
        )
