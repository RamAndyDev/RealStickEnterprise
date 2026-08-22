from __future__ import annotations

from datetime import datetime, time, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.core.roles import UserRole
from app.core.security import CurrentProfile
from app.modules.auth.provisioning import provision_auth_user
from app.modules.franchises.repository import FranchiseRepository
from app.modules.franchises.schemas import (
    FRANCHISE_DELETE_BLOCKED_DETAIL,
    OWNER_EMAIL_EXISTS_DETAIL,
    FranchiseApplicationSummary,
    FranchiseCreate,
    FranchiseDetail,
    FranchiseListItem,
    FranchiseListResponse,
    FranchiseOwnerAssign,
    FranchiseOwnerCreate,
    FranchiseOwnerCreateResponse,
    FranchiseOfflinePaymentCreate,
    FranchiseOwnerSummary,
    FranchisePaymentStatus,
    FranchisePaymentSummary,
    FranchiseStatus,
    FranchiseStatusUpdate,
    FranchiseUpdate,
    LaunchChecklistItem,
    LaunchChecklistItemUpdate,
)


class FranchiseService:
    def __init__(self, repo: FranchiseRepository | None = None) -> None:
        self.repo = repo or FranchiseRepository()

    def list_franchises(
        self,
        *,
        status: FranchiseStatus | None = None,
        search: str | None = None,
        include_archived: bool = False,
    ) -> FranchiseListResponse:
        rows = self.repo.list_franchises(
            status=status,
            search=search,
            include_archived=include_archived,
        )
        franchise_ids = [str(row['id']) for row in rows]
        owners = self.repo.list_owners_for_franchises(franchise_ids)
        owners_by_franchise = {str(o['franchise_id']): o for o in owners}
        payments = self.repo.latest_payment_status_map(franchise_ids)
        progress = self.repo.checklist_progress_map(franchise_ids)

        items = [
            self._to_list_item(
                row,
                owner=owners_by_franchise.get(str(row['id'])),
                payment_status=payments.get(str(row['id'])),
                progress=progress.get(str(row['id']), (0, 0)),
            )
            for row in rows
        ]
        return FranchiseListResponse(items=items, total=len(items))

    def get_franchise(self, franchise_id: UUID) -> FranchiseDetail:
        row = self.repo.get_franchise(franchise_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        owner = self.repo.get_active_owner(franchise_id)
        payments = self.repo.list_payments(franchise_id)
        applications = self.repo.list_applications_for_franchise(franchise_id)
        checklist = self.repo.list_checklist(franchise_id)
        payment_status = payments[0]['status'] if payments else None
        completed = sum(1 for item in checklist if item.get('is_completed'))

        base = self._to_list_item(
            row,
            owner=owner,
            payment_status=payment_status,
            progress=(completed, len(checklist)),
        )
        return FranchiseDetail(
            **base.model_dump(),
            settings=row.get('settings') or {},
            applications=[FranchiseApplicationSummary.model_validate(a) for a in applications],
            payments=[
                FranchisePaymentSummary(
                    id=p['id'],
                    amount=float(p['amount']),
                    currency=p.get('currency') or 'INR',
                    payment_method=p.get('payment_method'),
                    reference_number=p.get('reference_number'),
                    status=p['status'],
                    paid_at=p.get('paid_at'),
                    notes=p.get('notes'),
                    created_at=p['created_at'],
                    updated_at=p['updated_at'],
                )
                for p in payments
            ],
            launch_checklist=[LaunchChecklistItem.model_validate(i) for i in checklist],
        )

    def create_franchise(
        self,
        data: FranchiseCreate,
        actor: CurrentProfile | None = None,
    ) -> FranchiseDetail:
        owner_payload = data.owner_create_payload()
        if owner_payload:
            if actor is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Unable to create franchise owner',
                )
            self._reject_existing_owner_email(owner_payload.email)

        if data.code:
            existing = self.repo.get_franchise_by_code(data.code)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Franchise code already exists',
                )

        payload = {
            'name': data.name,
            'code': data.code,
            'owner_email': data.owner_email,
            'address': data.address,
            'city': data.city,
            'state': data.state,
            'postal_code': data.postal_code,
            'tier': data.tier,
            'status': data.status.value,
            'open_date': data.open_date.isoformat() if data.open_date else None,
            'employee_limit': data.employee_limit,
            'closed_at': (
                datetime.now(timezone.utc).isoformat()
                if data.status == FranchiseStatus.CLOSED
                else None
            ),
        }

        try:
            created = self.repo.create_franchise(payload)
        except Exception as exc:
            if self.repo.is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Franchise code already exists',
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to create franchise',
            ) from exc

        franchise_id = UUID(str(created['id']))
        if not owner_payload:
            self.repo.seed_default_checklist(franchise_id)
            return self.get_franchise(franchise_id)

        try:
            self.repo.seed_default_checklist(franchise_id)
            created_owner = self.create_owner(franchise_id, owner_payload, actor)
            return created_owner.franchise
        except HTTPException:
            self._rollback_new_franchise(franchise_id)
            raise
        except Exception as exc:
            self._rollback_new_franchise(franchise_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to create franchise',
            ) from exc

    def update_franchise(self, franchise_id: UUID, data: FranchiseUpdate) -> FranchiseDetail:
        existing = self.repo.get_franchise(franchise_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        updates = data.model_dump(exclude_unset=True)
        if 'open_date' in updates and updates['open_date'] is not None:
            updates['open_date'] = updates['open_date'].isoformat()

        if 'code' in updates and updates['code']:
            conflict = self.repo.get_franchise_by_code(updates['code'])
            if conflict and str(conflict['id']) != str(franchise_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Franchise code already exists',
                )

        if not updates:
            return self.get_franchise(franchise_id)

        try:
            self.repo.update_franchise(franchise_id, updates)
        except Exception as exc:
            if self.repo.is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Franchise code already exists',
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to update franchise',
            ) from exc

        return self.get_franchise(franchise_id)

    def update_status(self, franchise_id: UUID, data: FranchiseStatusUpdate) -> FranchiseDetail:
        existing = self.repo.get_franchise(franchise_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        payload: dict = {'status': data.status.value}
        if data.status == FranchiseStatus.CLOSED:
            payload['closed_at'] = datetime.now(timezone.utc).isoformat()
        elif existing.get('status') == FranchiseStatus.CLOSED.value:
            payload['closed_at'] = None

        try:
            self.repo.update_franchise(franchise_id, payload)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to update franchise status',
            ) from exc

        return self.get_franchise(franchise_id)

    def delete_franchise(self, franchise_id: UUID) -> None:
        existing = self.repo.get_franchise(franchise_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        if self.repo.franchise_has_business_references(franchise_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=FRANCHISE_DELETE_BLOCKED_DETAIL,
            )

        try:
            deleted = self.repo.delete_franchise(franchise_id)
        except Exception as exc:
            if self.repo.is_foreign_key_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=FRANCHISE_DELETE_BLOCKED_DETAIL,
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to delete franchise',
            ) from exc
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

    def assign_owner(
        self,
        franchise_id: UUID,
        data: FranchiseOwnerAssign,
        actor: CurrentProfile,
    ) -> FranchiseDetail:
        franchise = self.repo.get_franchise(franchise_id)
        if not franchise:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        profile = None
        resolved_email = data.owner_email

        if data.owner_profile_id is not None:
            profile = self.repo.get_profile(data.owner_profile_id)
            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Owner profile not found',
                )
        elif data.owner_email is not None:
            auth_user_id = self.repo.find_auth_user_id_by_email(data.owner_email)
            if not auth_user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='No auth user found for owner email',
                )
            profile = self.repo.get_profile(UUID(auth_user_id))
            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Owner profile not found for auth user',
                )
            resolved_email = data.owner_email

        assert profile is not None
        self._validate_assignable_profile(profile, franchise_id)
        self._link_owner_profile(
            franchise_id=franchise_id,
            profile=profile,
            owner_email=resolved_email,
            actor=actor,
        )
        return self.get_franchise(franchise_id)

    def create_owner(
        self,
        franchise_id: UUID,
        data: FranchiseOwnerCreate,
        actor: CurrentProfile,
    ) -> FranchiseOwnerCreateResponse:
        franchise = self.repo.get_franchise(franchise_id)
        if not franchise:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        self._reject_existing_owner_email(data.email)

        provisioned = provision_auth_user(
            self.repo,
            email=data.email,
            full_name=data.full_name,
            created_label='Franchise owner created',
            existing_conflict_detail=OWNER_EMAIL_EXISTS_DETAIL,
        )
        auth_user_id = provisioned.auth_user_id
        password_setup = provisioned.password_setup
        message = provisioned.message

        try:
            # Deactivate previous active owner before inserting the new active owner row.
            previous = self.repo.get_active_owner(franchise_id)
            if previous and str(previous['id']) != auth_user_id:
                self.repo.update_profile(UUID(str(previous['id'])), {'is_active': False})

            profile = self.repo.create_profile(
                {
                    'id': auth_user_id,
                    'full_name': data.full_name,
                    'role': UserRole.FRANCHISE_OWNER.value,
                    'franchise_id': str(franchise_id),
                    'phone': data.phone,
                    'is_active': True,
                }
            )
            self.repo.update_franchise(franchise_id, {'owner_email': data.email})
            self._complete_owner_assigned_checklist(franchise_id, actor)
        except Exception as exc:
            # Best-effort rollback of the Auth user if profile linkage fails.
            try:
                self.repo.delete_auth_user(auth_user_id)
            except Exception:
                pass
            if self.repo.is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Franchise already has an active owner or profile conflict',
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Unable to create franchise owner profile',
            ) from exc

        franchise_detail = self.get_franchise(franchise_id)
        owner = FranchiseOwnerSummary(
            id=profile['id'],
            full_name=profile['full_name'],
            email=data.email,
            phone=profile.get('phone'),
            is_active=bool(profile.get('is_active', True)),
        )
        return FranchiseOwnerCreateResponse(
            franchise=franchise_detail,
            owner=owner,
            password_setup=password_setup,
            message=message,
        )

    def _reject_existing_owner_email(self, email: str) -> None:
        if self.repo.find_auth_user_id_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=OWNER_EMAIL_EXISTS_DETAIL,
            )

    def _rollback_new_franchise(self, franchise_id: UUID) -> None:
        try:
            self.repo.delete_new_franchise(franchise_id)
        except Exception:
            pass

    def _validate_assignable_profile(self, profile: dict, franchise_id: UUID) -> None:
        try:
            role = UserRole(profile['role'])
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Owner profile has an invalid role',
            ) from exc

        if role == UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='SYSTEM_ADMIN cannot be assigned as franchise owner',
            )

        if not profile.get('is_active', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Owner profile is inactive',
            )

        current_franchise = profile.get('franchise_id')
        if (
            current_franchise
            and str(current_franchise) != str(franchise_id)
            and role == UserRole.FRANCHISE_OWNER
            and profile.get('is_active')
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Profile is already an active owner of another franchise',
            )

    def _link_owner_profile(
        self,
        *,
        franchise_id: UUID,
        profile: dict,
        owner_email: str | None,
        actor: CurrentProfile,
    ) -> None:
        previous = self.repo.get_active_owner(franchise_id)
        if previous and str(previous['id']) != str(profile['id']):
            try:
                self.repo.update_profile(
                    UUID(str(previous['id'])),
                    {'is_active': False},
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail='Unable to reassign previous franchise owner',
                ) from exc

        try:
            self.repo.update_profile(
                UUID(str(profile['id'])),
                {
                    'role': UserRole.FRANCHISE_OWNER.value,
                    'franchise_id': str(franchise_id),
                    'is_active': True,
                },
            )
        except Exception as exc:
            if self.repo.is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Franchise already has an active owner',
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Unable to assign franchise owner',
            ) from exc

        if owner_email:
            self.repo.update_franchise(franchise_id, {'owner_email': owner_email})

        self._complete_owner_assigned_checklist(franchise_id, actor)

    def _complete_owner_assigned_checklist(
        self,
        franchise_id: UUID,
        actor: CurrentProfile,
    ) -> None:
        checklist = self.repo.list_checklist(franchise_id)
        for item in checklist:
            if item.get('item_key') == 'owner_assigned' and not item.get('is_completed'):
                self.repo.update_checklist_item(
                    franchise_id,
                    UUID(str(item['id'])),
                    {
                        'is_completed': True,
                        'completed_at': datetime.now(timezone.utc).isoformat(),
                        'completed_by': str(actor.id),
                    },
                )
                break

    def list_applications(
        self,
        *,
        status: str | None = None,
        search: str | None = None,
    ) -> list[FranchiseApplicationSummary]:
        rows = self.repo.list_applications(status=status, search=search)
        return [FranchiseApplicationSummary.model_validate(row) for row in rows]

    def get_application(self, application_id: UUID) -> FranchiseApplicationSummary:
        row = self.repo.get_application(application_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Franchise application not found',
            )
        return FranchiseApplicationSummary.model_validate(row)

    def get_launch_progress(self, franchise_id: UUID) -> list[LaunchChecklistItem]:
        if not self.repo.get_franchise(franchise_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')
        rows = self.repo.list_checklist(franchise_id)
        if not rows:
            rows = self.repo.seed_default_checklist(franchise_id)
        return [LaunchChecklistItem.model_validate(row) for row in rows]

    def update_launch_item(
        self,
        franchise_id: UUID,
        item_id: UUID,
        data: LaunchChecklistItemUpdate,
        actor: CurrentProfile,
    ) -> LaunchChecklistItem:
        if not self.repo.get_franchise(franchise_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        payload: dict = {'is_completed': data.is_completed}
        if data.is_completed:
            payload['completed_at'] = datetime.now(timezone.utc).isoformat()
            payload['completed_by'] = str(actor.id)
        else:
            payload['completed_at'] = None
            payload['completed_by'] = None

        updated = self.repo.update_checklist_item(franchise_id, item_id, payload)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Launch checklist item not found',
            )
        return LaunchChecklistItem.model_validate(updated)

    def record_offline_payment(
        self,
        franchise_id: UUID,
        data: FranchiseOfflinePaymentCreate,
    ) -> FranchiseDetail:
        if not self.repo.get_franchise(franchise_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        paid_at = datetime.combine(data.paid_at, time(12, 0), tzinfo=timezone.utc)
        payload = {
            'franchise_id': str(franchise_id),
            'amount': float(data.amount),
            'currency': 'INR',
            'payment_method': data.payment_method.value,
            'reference_number': data.reference_number,
            'status': FranchisePaymentStatus.COMPLETED.value,
            'paid_at': paid_at.isoformat(),
            'notes': data.notes,
        }
        try:
            self.repo.create_payment(payload)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to record franchise payment',
            ) from exc

        return self.get_franchise(franchise_id)

    def _to_list_item(
        self,
        row: dict,
        *,
        owner: dict | None,
        payment_status: str | None,
        progress: tuple[int, int],
    ) -> FranchiseListItem:
        owner_summary = None
        if owner:
            owner_summary = FranchiseOwnerSummary(
                id=owner['id'],
                full_name=owner['full_name'],
                email=None,
                phone=owner.get('phone'),
                is_active=bool(owner.get('is_active', True)),
            )
        return FranchiseListItem(
            id=row['id'],
            name=row['name'],
            code=row.get('code'),
            owner_email=row.get('owner_email'),
            address=row.get('address'),
            city=row.get('city'),
            state=row.get('state'),
            postal_code=row.get('postal_code'),
            tier=row.get('tier'),
            status=FranchiseStatus(row['status']),
            open_date=row.get('open_date'),
            closed_at=row.get('closed_at'),
            employee_limit=row.get('employee_limit') or 10,
            is_archived=bool(row.get('is_archived', False)),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            owner=owner_summary,
            payment_status=payment_status,
            launch_progress_completed=progress[0],
            launch_progress_total=progress[1],
        )
