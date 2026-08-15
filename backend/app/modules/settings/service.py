from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.core.gst import split_gst_rate
from app.modules.settings.repository import SettingsRepository
from app.modules.settings.schemas import (
    GstSettings,
    GstUpdate,
    Offer,
    OfferCreate,
    OfferListResponse,
    OfferUpdate,
    offer_from_row,
)


def _gst_from_row(row: dict) -> GstSettings:
    rate = row['rate']
    cgst_rate, sgst_rate = split_gst_rate(rate)
    return GstSettings(
        id=row['id'],
        rate=float(rate),
        cgst_rate=float(cgst_rate),
        sgst_rate=float(sgst_rate),
        is_active=bool(row.get('is_active', True)),
        created_at=row.get('created_at'),
        updated_at=row.get('updated_at'),
    )


class SettingsService:
    def __init__(self, repo: SettingsRepository | None = None) -> None:
        self.repo = repo or SettingsRepository()

    def get_gst(self) -> GstSettings:
        row = self.repo.get_active_gst()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='GST is not configured',
            )
        try:
            return _gst_from_row(row)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='GST is not configured',
            ) from exc

    def update_gst(self, body: GstUpdate) -> GstSettings:
        rate = float(body.rate)
        existing = self.repo.get_active_gst()
        try:
            if existing:
                row = self.repo.update_gst(existing['id'], {'rate': rate})
            else:
                row = self.repo.create_gst({'rate': rate, 'is_active': True})
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to update GST',
            ) from exc
        return _gst_from_row(row)

    def list_offers(self) -> OfferListResponse:
        items = [offer_from_row(row) for row in self.repo.list_offers()]
        return OfferListResponse(items=items, total=len(items))

    def create_offer(self, body: OfferCreate) -> Offer:
        if body.franchise_id and not self.repo.franchise_exists(body.franchise_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')
        payload = {
            'name': body.name,
            'description': body.description,
            'discount_type': body.discount_type.value,
            'discount_value': float(body.discount_value),
            'is_active': body.is_active,
            'valid_from': body.valid_from.isoformat() if body.valid_from else None,
            'valid_to': body.valid_to.isoformat() if body.valid_to else None,
            'franchise_id': str(body.franchise_id) if body.franchise_id else None,
        }
        try:
            created = self.repo.create_offer(payload)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to create offer',
            ) from exc
        return offer_from_row(created)

    def update_offer(self, offer_id: UUID, body: OfferUpdate) -> Offer:
        existing = self.repo.get_offer(offer_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Offer not found')

        updates = body.model_dump(exclude_unset=True)
        payload: dict = {}
        if 'name' in updates:
            payload['name'] = body.name
        if 'description' in updates:
            payload['description'] = body.description
        if body.discount_type is not None:
            payload['discount_type'] = body.discount_type.value
        if body.discount_value is not None:
            payload['discount_value'] = float(body.discount_value)
        if body.is_active is not None:
            payload['is_active'] = body.is_active
        if 'valid_from' in updates:
            payload['valid_from'] = body.valid_from.isoformat() if body.valid_from else None
        if 'valid_to' in updates:
            payload['valid_to'] = body.valid_to.isoformat() if body.valid_to else None
        if body.clear_valid_from:
            payload['valid_from'] = None
        if body.clear_valid_to:
            payload['valid_to'] = None
        if 'franchise_id' in updates:
            if body.franchise_id and not self.repo.franchise_exists(body.franchise_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Franchise not found',
                )
            payload['franchise_id'] = str(body.franchise_id) if body.franchise_id else None
        if body.clear_franchise_id:
            payload['franchise_id'] = None

        next_from = payload['valid_from'] if 'valid_from' in payload else existing.get('valid_from')
        next_to = payload['valid_to'] if 'valid_to' in payload else existing.get('valid_to')
        if next_from and next_to and str(next_from) > str(next_to):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='valid_from must be on or before valid_to',
            )

        if not payload:
            return offer_from_row(existing)
        try:
            updated = self.repo.update_offer(offer_id, payload)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to update offer',
            ) from exc
        return offer_from_row(updated)
