from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.core.roles import UserRole
from app.core.security import CurrentProfile, require_role
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
    ProductCategoryUpdate,
    ProductCreate,
    ProductListResponse,
    ProductUpdate,
)
from app.modules.products.service import ProductService

router = APIRouter(prefix='/admin', tags=['admin-products'])
owner_router = APIRouter(prefix='/owner', tags=['owner-menu'])

SystemAdmin = Annotated[CurrentProfile, Depends(require_role(UserRole.SYSTEM_ADMIN))]
FranchiseOwner = Annotated[CurrentProfile, Depends(require_role(UserRole.FRANCHISE_OWNER))]


def get_product_service() -> ProductService:
    return ProductService()


# ── Categories ──────────────────────────────────────────────────────────────


@router.get('/product-categories', response_model=ProductCategoryListResponse)
def list_product_categories(
    _: SystemAdmin,
    include_inactive: bool = Query(default=True),
    service: ProductService = Depends(get_product_service),
) -> ProductCategoryListResponse:
    return service.list_categories(include_inactive=include_inactive)


@router.post('/product-categories', response_model=ProductCategory, status_code=201)
def create_product_category(
    body: ProductCategoryCreate,
    _: SystemAdmin,
    service: ProductService = Depends(get_product_service),
) -> ProductCategory:
    return service.create_category(body)


@router.patch('/product-categories/{category_id}', response_model=ProductCategory)
def update_product_category(
    category_id: UUID,
    body: ProductCategoryUpdate,
    _: SystemAdmin,
    service: ProductService = Depends(get_product_service),
) -> ProductCategory:
    return service.update_category(category_id, body)


@router.delete('/product-categories/{category_id}', status_code=204)
def delete_product_category(
    category_id: UUID,
    _: SystemAdmin,
    service: ProductService = Depends(get_product_service),
) -> None:
    service.delete_category(category_id)


# ── Products ────────────────────────────────────────────────────────────────


@router.get('/products', response_model=ProductListResponse)
def list_products(
    _: SystemAdmin,
    category_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    is_active: bool | None = Query(default=None),
    service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    return service.list_products(
        category_id=category_id,
        search=search,
        is_active=is_active,
    )


@router.post('/products', response_model=Product, status_code=201)
def create_product(
    body: ProductCreate,
    _: SystemAdmin,
    service: ProductService = Depends(get_product_service),
) -> Product:
    return service.create_product(body)


@router.get('/products/{product_id}', response_model=Product)
def get_product(
    product_id: UUID,
    _: SystemAdmin,
    service: ProductService = Depends(get_product_service),
) -> Product:
    return service.get_product(product_id)


@router.patch('/products/{product_id}', response_model=Product)
def update_product(
    product_id: UUID,
    body: ProductUpdate,
    _: SystemAdmin,
    service: ProductService = Depends(get_product_service),
) -> Product:
    return service.update_product(product_id, body)


@router.post('/products/{product_id}/image', response_model=Product)
async def upload_product_image(
    product_id: UUID,
    _: SystemAdmin,
    file: UploadFile = File(...),
    service: ProductService = Depends(get_product_service),
) -> Product:
    return await service.upload_product_image(product_id, file)


@router.delete('/products/{product_id}/image', response_model=Product)
def remove_product_image(
    product_id: UUID,
    _: SystemAdmin,
    service: ProductService = Depends(get_product_service),
) -> Product:
    return service.remove_product_image(product_id)


# ── Franchise product assignments ───────────────────────────────────────────


@router.get(
    '/franchises/{franchise_id}/products',
    response_model=FranchiseProductListResponse,
)
def list_franchise_products(
    franchise_id: UUID,
    _: SystemAdmin,
    service: ProductService = Depends(get_product_service),
) -> FranchiseProductListResponse:
    return service.list_franchise_products(franchise_id)


@router.post(
    '/franchises/{franchise_id}/products',
    response_model=FranchiseProductAssignment,
    status_code=201,
)
def assign_franchise_product(
    franchise_id: UUID,
    body: FranchiseProductAssign,
    _: SystemAdmin,
    service: ProductService = Depends(get_product_service),
) -> FranchiseProductAssignment:
    return service.assign_franchise_product(franchise_id, body)


@router.patch(
    '/franchises/{franchise_id}/products/{product_id}',
    response_model=FranchiseProductAssignment,
)
def update_franchise_product(
    franchise_id: UUID,
    product_id: UUID,
    body: FranchiseProductUpdate,
    _: SystemAdmin,
    service: ProductService = Depends(get_product_service),
) -> FranchiseProductAssignment:
    return service.update_franchise_product(franchise_id, product_id, body)


# ── Franchise owner menu ────────────────────────────────────────────────────


@owner_router.get('/menu', response_model=FranchiseProductListResponse)
def list_owner_menu(
    profile: FranchiseOwner,
    service: ProductService = Depends(get_product_service),
) -> FranchiseProductListResponse:
    return service.list_owner_menu(profile)


@owner_router.patch('/menu/{product_id}', response_model=FranchiseProductAssignment)
def update_owner_menu_item(
    product_id: UUID,
    body: OwnerFranchiseProductUpdate,
    profile: FranchiseOwner,
    service: ProductService = Depends(get_product_service),
) -> FranchiseProductAssignment:
    return service.update_owner_menu_item(profile, product_id, body)
