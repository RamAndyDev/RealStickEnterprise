from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.modules.public.email import CONTACT_FAILURE_MESSAGE, EmailDeliveryError, send_contact_email
from app.modules.public.rate_limit import contact_rate_limited
from app.modules.public.repository import PublicCatalogRepository
from app.core.config import get_settings
from app.modules.public.schemas import (
    ENQUIRY_TYPE_LABELS,
    ContactEnquiryRequest,
    ContactEnquiryResponse,
    PublicCategory,
    PublicCategoryListResponse,
    PublicContactOptions,
    PublicProduct,
    PublicProductListResponse,
)

THANK_YOU_MESSAGE = 'Thank you. The RealStick team will contact you.'


def client_ip(request: Request) -> str:
    forwarded = request.headers.get('x-forwarded-for')
    if forwarded:
        return forwarded.split(',')[0].strip() or 'unknown'
    if request.client and request.client.host:
        return request.client.host
    return 'unknown'


class PublicService:
    def __init__(self, repo: PublicCatalogRepository | None = None) -> None:
        self.repo = repo or PublicCatalogRepository()

    def list_categories(self) -> PublicCategoryListResponse:
        rows = self.repo.list_active_categories()
        items = [PublicCategory.model_validate(row) for row in rows]
        return PublicCategoryListResponse(items=items, total=len(items))

    def list_products(self) -> PublicProductListResponse:
        categories = {str(row['id']): row for row in self.repo.list_active_categories()}
        products: list[PublicProduct] = []
        for row in self.repo.list_active_products():
            category_id = row.get('category_id')
            if not category_id:
                continue
            category = categories.get(str(category_id))
            if not category:
                continue
            products.append(
                PublicProduct(
                    id=row['id'],
                    category_id=category_id,
                    category_name=category['name'],
                    name=row['name'],
                    description=row.get('description'),
                    image_url=row.get('image_url'),
                )
            )
        return PublicProductListResponse(items=products, total=len(products))

    def submit_contact(self, request: Request, body: ContactEnquiryRequest) -> ContactEnquiryResponse:
        if body.website:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Unable to send your enquiry right now. Please try again.',
            )
        if contact_rate_limited(client_ip(request)):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=CONTACT_FAILURE_MESSAGE,
            )
        try:
            send_contact_email(
                name=body.name,
                phone=body.phone,
                email=str(body.email),
                message=body.message,
                enquiry_type=ENQUIRY_TYPE_LABELS.get(body.enquiry_type, body.enquiry_type.value),
            )
        except EmailDeliveryError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc) or CONTACT_FAILURE_MESSAGE,
            ) from exc
        return ContactEnquiryResponse(message=THANK_YOU_MESSAGE)

    def contact_options(self) -> PublicContactOptions:
        settings = get_settings()
        phone = _digits_or_none(settings.public_contact_phone)
        whatsapp = _digits_or_none(settings.public_contact_whatsapp)
        email = (settings.public_contact_email or '').strip() or None
        return PublicContactOptions(
            phone=phone,
            whatsapp=whatsapp,
            email=email,
            whatsapp_url=f'https://wa.me/{whatsapp}' if whatsapp else None,
            tel_url=f'tel:{phone}' if phone else None,
            mailto_url=f'mailto:{email}' if email else None,
        )


def _digits_or_none(value: str | None) -> str | None:
    if not value:
        return None
    digits = ''.join(ch for ch in value if ch.isdigit())
    return digits or None
