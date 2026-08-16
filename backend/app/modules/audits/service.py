from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import HTTPException, status

from app.core.roles import UserRole
from app.core.security import CurrentProfile
from app.modules.audits.repository import AuditsRepository
from app.modules.audits.schemas import (
    AuditCreate,
    AuditDetail,
    AuditItem,
    AuditItemInput,
    AuditListItem,
    AuditListResponse,
    FranchiseAuditStatus,
)
from app.modules.reports.dates import resolve_sales_date

# Canonical operational checklist. Backend is authoritative.
# Do not persist this as a table; snapshot checklist_item text on each audit.
FRANCHISE_OPERATIONAL_CHECKLIST: list[dict[str, str | int]] = [
    {'item_key': 'pos_working', 'label': 'POS system working', 'display_order': 1},
    {'item_key': 'internet_working', 'label': 'Internet connection working', 'display_order': 2},
    {
        'item_key': 'receipt_printer_working',
        'label': 'Receipt printer working',
        'display_order': 3,
    },
    {
        'item_key': 'product_menu_correct',
        'label': 'Product/menu information correct',
        'display_order': 4,
    },
    {
        'item_key': 'selling_prices_correct',
        'label': 'Product selling prices correct',
        'display_order': 5,
    },
    {
        'item_key': 'product_availability_correct',
        'label': 'Product availability correct',
        'display_order': 6,
    },
    {
        'item_key': 'billing_process_working',
        'label': 'Billing process working',
        'display_order': 7,
    },
    {
        'item_key': 'payment_methods_working',
        'label': 'Payment methods working',
        'display_order': 8,
    },
    {
        'item_key': 'store_presentation',
        'label': 'Store/product presentation satisfactory',
        'display_order': 9,
    },
    {
        'item_key': 'general_operation',
        'label': 'General cleanliness/operation satisfactory',
        'display_order': 10,
    },
]

_CHECKLIST_BY_KEY = {str(item['item_key']): item for item in FRANCHISE_OPERATIONAL_CHECKLIST}
_CANONICAL_KEYS = frozenset(_CHECKLIST_BY_KEY)


def calculate_overall_status(statuses: list[FranchiseAuditStatus]) -> FranchiseAuditStatus:
    if any(item == FranchiseAuditStatus.FAIL for item in statuses):
        return FranchiseAuditStatus.FAIL
    if any(item == FranchiseAuditStatus.NEEDS_ATTENTION for item in statuses):
        return FranchiseAuditStatus.NEEDS_ATTENTION
    return FranchiseAuditStatus.PASS


class AuditsService:
    def __init__(self, repo: AuditsRepository | None = None) -> None:
        self.repo = repo or AuditsRepository()

    def list_audits(
        self,
        profile: CurrentProfile,
        *,
        franchise_id: UUID | None,
        from_date: date | None,
        to_date: date | None,
        overall_status: FranchiseAuditStatus | None,
        page: int,
        page_size: int,
    ) -> AuditListResponse:
        scoped = self._list_franchise_scope(profile, franchise_id)
        if from_date is not None and to_date is not None and from_date > to_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='from_date must be on or before to_date',
            )

        rows, total = self.repo.list_audits(
            franchise_id=scoped,
            from_date=from_date,
            to_date=to_date,
            overall_status=overall_status.value if overall_status else None,
            page=page,
            page_size=page_size,
        )
        items = [self._to_list_item(row) for row in rows]
        return AuditListResponse(items=items, page=page, page_size=page_size, total=total)

    def get_audit(self, profile: CurrentProfile, audit_id: UUID) -> AuditDetail:
        row = self.repo.get_audit(audit_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Audit not found')
        self._assert_can_read_audit(profile, UUID(str(row['franchise_id'])))
        items = self.repo.list_items(audit_id)
        return self._to_detail(row, items)

    def create_audit(self, profile: CurrentProfile, body: AuditCreate) -> AuditDetail:
        franchise_id = self._create_franchise_id(profile, body.franchise_id)
        audit_date = self._validated_audit_date(body.audit_date)
        self._validate_checklist(body.items)

        franchise = self.repo.get_franchise(franchise_id)
        if not franchise:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        overall_status = calculate_overall_status([item.status for item in body.items])
        items_by_key = {item.item_key: item for item in body.items}
        item_payloads = [
            {
                'item_key': str(canonical['item_key']),
                'checklist_item': str(canonical['label']),
                'display_order': int(canonical['display_order']),
                'status': items_by_key[str(canonical['item_key'])].status.value,
                'remarks': items_by_key[str(canonical['item_key'])].remarks,
            }
            for canonical in FRANCHISE_OPERATIONAL_CHECKLIST
        ]

        audit_payload = {
            'franchise_id': str(franchise_id),
            'franchise_name_snapshot': franchise['name'],
            'audit_date': audit_date.isoformat(),
            'auditor_id': str(profile.id),
            'auditor_name_snapshot': profile.full_name,
            'overall_status': overall_status.value,
            'remarks': body.remarks,
        }

        created, items = self.repo.create_audit_with_items(audit_payload, item_payloads)
        return self._to_detail(created, items)

    def _create_franchise_id(
        self,
        profile: CurrentProfile,
        requested: UUID | None,
    ) -> UUID:
        if profile.role == UserRole.FRANCHISE_OWNER:
            if profile.franchise_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Profile must belong to a franchise',
                )
            return profile.franchise_id
        if profile.role != UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions for this resource',
            )
        if requested is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='franchise_id is required',
            )
        return requested

    def _list_franchise_scope(
        self,
        profile: CurrentProfile,
        requested: UUID | None,
    ) -> UUID | None:
        if profile.role == UserRole.FRANCHISE_OWNER:
            if profile.franchise_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Profile must belong to a franchise',
                )
            return profile.franchise_id
        if profile.role != UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions for this resource',
            )
        return requested

    def _assert_can_read_audit(self, profile: CurrentProfile, franchise_id: UUID) -> None:
        if profile.role == UserRole.SYSTEM_ADMIN:
            return
        if profile.franchise_id is None or profile.franchise_id != franchise_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Audit not found')

    def _validated_audit_date(self, value: date) -> date:
        try:
            return resolve_sales_date(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    def _validate_checklist(self, items: list[AuditItemInput]) -> None:
        if len(items) != len(FRANCHISE_OPERATIONAL_CHECKLIST):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='Exactly 10 checklist items are required',
            )
        keys = [item.item_key for item in items]
        if len(keys) != len(set(keys)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='Duplicate checklist item keys are not allowed',
            )
        provided = set(keys)
        if provided != _CANONICAL_KEYS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='Checklist must include all canonical items and no unknown items',
            )

    def _to_list_item(self, row: dict) -> AuditListItem:
        return AuditListItem(
            id=row['id'],
            franchise_id=row['franchise_id'],
            franchise_name=row['franchise_name_snapshot'],
            audit_date=row['audit_date'],
            auditor_id=row.get('auditor_id'),
            auditor_name=row['auditor_name_snapshot'],
            overall_status=row['overall_status'],
            created_at=row['created_at'],
        )

    def _to_detail(self, row: dict, items: list[dict]) -> AuditDetail:
        ordered = sorted(items, key=lambda item: int(item.get('display_order') or 0))
        return AuditDetail(
            id=row['id'],
            franchise_id=row['franchise_id'],
            franchise_name=row['franchise_name_snapshot'],
            audit_date=row['audit_date'],
            auditor_id=row.get('auditor_id'),
            auditor_name=row['auditor_name_snapshot'],
            overall_status=row['overall_status'],
            remarks=row.get('remarks'),
            created_at=row['created_at'],
            updated_at=row.get('updated_at') or row['created_at'],
            items=[
                AuditItem(
                    id=item['id'],
                    item_key=item['item_key'],
                    checklist_item=item['checklist_item'],
                    display_order=int(item['display_order']),
                    status=item['status'],
                    remarks=item.get('remarks'),
                )
                for item in ordered
            ],
        )
