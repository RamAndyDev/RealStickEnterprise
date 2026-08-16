from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.core.gst import split_gst_rate
from app.core.security import CurrentProfile
from app.modules.settings.repository import SettingsRepository
from app.modules.settings.schemas import (
    GstSettings,
    GstUpdate,
    Offer,
    OfferCreate,
    OfferListResponse,
    OfferUpdate,
    Promotion,
    PromotionCreate,
    PromotionListResponse,
    PromotionUpdate,
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
            'promotion_id': str(body.promotion_id) if body.promotion_id else None,
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
        if 'promotion_id' in updates:
            payload['promotion_id'] = str(body.promotion_id) if body.promotion_id else None
        if body.clear_promotion_id:
            payload['promotion_id'] = None

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

    def list_owner_offers(self, owner: CurrentProfile) -> OfferListResponse:
        franchise_id = self._owner_franchise_id(owner)
        rows = self.repo.list_offers_for_franchise(franchise_id)
        items = [self._offer_with_promotion(row) for row in rows]
        return OfferListResponse(items=items, total=len(items))

    def create_owner_offer(self, owner: CurrentProfile, body: OfferCreate) -> Offer:
        franchise_id = self._owner_franchise_id(owner)
        promotion_id = body.promotion_id
        if promotion_id:
            self._assert_owner_may_use_promotion(franchise_id, promotion_id)
        payload = {
            'name': body.name,
            'description': body.description,
            'discount_type': body.discount_type.value,
            'discount_value': float(body.discount_value),
            'is_active': body.is_active,
            'valid_from': body.valid_from.isoformat() if body.valid_from else None,
            'valid_to': body.valid_to.isoformat() if body.valid_to else None,
            'franchise_id': str(franchise_id),
            'promotion_id': str(promotion_id) if promotion_id else None,
            'created_by': str(owner.id),
        }
        try:
            created = self.repo.create_offer(payload)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to create offer',
            ) from exc
        return self._offer_with_promotion(created)

    def update_owner_offer(
        self,
        owner: CurrentProfile,
        offer_id: UUID,
        body: OfferUpdate,
    ) -> Offer:
        franchise_id = self._owner_franchise_id(owner)
        existing = self.repo.get_offer(offer_id)
        if not existing or str(existing.get('franchise_id')) != str(franchise_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Offer not found')

        updates = body.model_dump(exclude_unset=True)
        if 'franchise_id' in updates or body.clear_franchise_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Franchise owner cannot move an offer to another franchise',
            )

        next_promotion = existing.get('promotion_id')
        if 'promotion_id' in updates:
            next_promotion = body.promotion_id
        if body.clear_promotion_id:
            next_promotion = None
        if next_promotion:
            self._assert_owner_may_use_promotion(franchise_id, UUID(str(next_promotion)))

        return self.update_offer(offer_id, body)

    def list_owner_promotions(self, owner: CurrentProfile) -> PromotionListResponse:
        franchise_id = self._owner_franchise_id(owner)
        items = [
            item
            for item in self.list_promotions().items
            if str(franchise_id) in {str(fid) for fid in item.franchise_ids}
        ]
        return PromotionListResponse(items=items, total=len(items))

    def list_promotions(self) -> PromotionListResponse:
        rows = self.repo.list_promotions()
        mapping = self.repo.list_promotion_franchise_map([str(row['id']) for row in rows])
        items = [self._promotion_from_row(row, mapping.get(str(row['id']), [])) for row in rows]
        return PromotionListResponse(items=items, total=len(items))

    def create_promotion(self, body: PromotionCreate, actor: CurrentProfile) -> Promotion:
        for franchise_id in body.franchise_ids:
            if not self.repo.franchise_exists(franchise_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')
        if self.repo.get_promotion_by_code(body.promo_code):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Promo code is already in use',
            )
        payload = {
            'name': body.name,
            'description': body.description,
            'promo_code': body.promo_code.strip(),
            'is_active': body.is_active,
            'valid_from': body.valid_from.isoformat() if body.valid_from else None,
            'valid_to': body.valid_to.isoformat() if body.valid_to else None,
            'created_by': str(actor.id),
        }
        try:
            created = self.repo.create_promotion(payload)
            self.repo.replace_promotion_franchises(
                created['id'],
                body.franchise_ids,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to create promotion',
            ) from exc
        return self._promotion_from_row(created, [str(fid) for fid in body.franchise_ids])

    def update_promotion(self, promotion_id: UUID, body: PromotionUpdate) -> Promotion:
        existing = self.repo.get_promotion(promotion_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Promotion not found')

        updates = body.model_dump(exclude_unset=True)
        payload: dict = {}
        if 'name' in updates:
            payload['name'] = body.name
        if 'description' in updates:
            payload['description'] = body.description
        if 'promo_code' in updates and body.promo_code:
            conflict = self.repo.get_promotion_by_code(body.promo_code)
            if conflict and str(conflict['id']) != str(promotion_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Promo code is already in use',
                )
            payload['promo_code'] = body.promo_code.strip()
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

        next_from = payload['valid_from'] if 'valid_from' in payload else existing.get('valid_from')
        next_to = payload['valid_to'] if 'valid_to' in payload else existing.get('valid_to')
        if next_from and next_to and str(next_from) > str(next_to):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='valid_from must be on or before valid_to',
            )

        try:
            updated = self.repo.update_promotion(promotion_id, payload) if payload else existing
            if body.franchise_ids is not None:
                for franchise_id in body.franchise_ids:
                    if not self.repo.franchise_exists(franchise_id):
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail='Franchise not found',
                        )
                self.repo.replace_promotion_franchises(promotion_id, body.franchise_ids)
                franchise_ids = [str(fid) for fid in body.franchise_ids]
            else:
                franchise_ids = self.repo.list_promotion_franchises(promotion_id)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to update promotion',
            ) from exc
        return self._promotion_from_row(updated, franchise_ids)

    def _owner_franchise_id(self, owner: CurrentProfile) -> UUID:
        if owner.franchise_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Franchise owner profile must belong to a franchise',
            )
        return owner.franchise_id

    def _assert_owner_may_use_promotion(self, franchise_id: UUID, promotion_id: UUID) -> None:
        promotion = self.repo.get_promotion(promotion_id)
        if not promotion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Promotion not found')
        if not self.repo.franchise_participates(promotion_id, franchise_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Promotion is not applicable to this franchise',
            )

    def _offer_with_promotion(self, row: dict) -> Offer:
        promotion_id = row.get('promotion_id')
        extra = dict(row)
        if promotion_id:
            promotion = self.repo.get_promotion(UUID(str(promotion_id)))
            if promotion:
                extra['promotion_name'] = promotion.get('name')
                extra['promotion_promo_code'] = promotion.get('promo_code')
        return offer_from_row(extra)

    def _promotion_from_row(self, row: dict, franchise_ids: list[str]) -> Promotion:
        return Promotion(
            id=row['id'],
            name=row['name'],
            description=row.get('description'),
            promo_code=row['promo_code'],
            valid_from=row.get('valid_from'),
            valid_to=row.get('valid_to'),
            is_active=bool(row.get('is_active', True)),
            franchise_ids=franchise_ids,
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
        )
