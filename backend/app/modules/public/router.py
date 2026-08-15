from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.modules.public.schemas import (
    ContactEnquiryRequest,
    ContactEnquiryResponse,
    PublicCategoryListResponse,
    PublicProductListResponse,
)
from app.modules.public.service import PublicService

router = APIRouter(prefix='/public', tags=['public'])


def get_public_service() -> PublicService:
    return PublicService()


@router.get('/categories', response_model=PublicCategoryListResponse)
def list_public_categories(
    service: PublicService = Depends(get_public_service),
) -> PublicCategoryListResponse:
    return service.list_categories()


@router.get('/products', response_model=PublicProductListResponse)
def list_public_products(
    service: PublicService = Depends(get_public_service),
) -> PublicProductListResponse:
    return service.list_products()


@router.post('/contact', response_model=ContactEnquiryResponse)
def submit_contact(
    request: Request,
    body: ContactEnquiryRequest,
    service: PublicService = Depends(get_public_service),
) -> ContactEnquiryResponse:
    return service.submit_contact(request, body)
