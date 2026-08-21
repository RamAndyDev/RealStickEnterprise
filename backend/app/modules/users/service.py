from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.core.roles import UserRole
from app.core.security import CurrentProfile
from app.modules.auth.identity import employee_auth_identity, is_internal_employee_identity
from app.modules.auth.provisioning import (
    AuthProvisionResult,
    _extract_user_id,
    provision_auth_user,
    send_password_recovery_email,
)
from app.modules.franchises.schemas import FranchiseOwnerCreate
from app.modules.franchises.service import FranchiseService
from app.modules.users.repository import UsersRepository
from app.modules.users.schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeePasswordResetRequest,
    EmployeeUpdate,
    ManagedUser,
    PasswordResetResponse,
    UserCreateResponse,
    UserListResponse,
)


_ADMIN_MANAGED_ROLES = (UserRole.SYSTEM_ADMIN.value, UserRole.FRANCHISE_OWNER.value)


class UsersService:
    def __init__(self, repo: UsersRepository | None = None) -> None:
        self.repo = repo or UsersRepository()

    def list_users(
        self,
        *,
        role: UserRole | None = None,
        franchise_id: UUID | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> UserListResponse:
        if role == UserRole.EMPLOYEE:
            return UserListResponse(items=[], total=0)

        rows = self.repo.list_profiles(
            role=role.value if role else None,
            roles=None if role else list(_ADMIN_MANAGED_ROLES),
            franchise_id=franchise_id,
            is_active=is_active,
        )
        items = self._hydrate(rows)
        if search:
            needle = search.strip().lower()
            items = [
                item
                for item in items
                if needle in item.full_name.lower()
                or needle in (item.email or '').lower()
                or needle in (item.phone or '').lower()
                or needle in (item.login_id or '').lower()
                or needle in (item.franchise_name or '').lower()
            ]
        return UserListResponse(items=items, total=len(items))

    def get_user(self, user_id: UUID) -> ManagedUser:
        row = self._admin_managed_profile(user_id)
        return self._hydrate([row])[0]

    def create_user(self, data: AdminUserCreate, actor: CurrentProfile) -> UserCreateResponse:
        if data.role == UserRole.EMPLOYEE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Employees are managed by franchise owners',
            )
        if data.role == UserRole.FRANCHISE_OWNER:
            if data.franchise_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Franchise owner must belong to a franchise',
                )
            created = FranchiseService().create_owner(
                data.franchise_id,
                FranchiseOwnerCreate(
                    full_name=data.full_name,
                    email=data.email,
                    phone=data.phone,
                ),
                actor,
            )
            user = self.get_user(created.owner.id)
            return UserCreateResponse(
                user=user,
                password_setup=created.password_setup,
                message=created.message,
            )

        return self._create_system_admin(data.full_name, data.email, data.phone)

    def update_user(self, user_id: UUID, data: AdminUserUpdate, actor: CurrentProfile) -> ManagedUser:
        existing = self._admin_managed_profile(user_id)

        try:
            role = UserRole(existing['role'])
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='User profile has an invalid role',
            ) from exc

        updates = data.model_dump(exclude_unset=True)
        reassignment_requested = 'franchise_id' in data.model_fields_set
        new_franchise_id = updates.pop('franchise_id', None) if reassignment_requested else None

        if role == UserRole.SYSTEM_ADMIN and reassignment_requested and new_franchise_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='SYSTEM_ADMIN cannot be assigned to a franchise',
            )

        if (
            reassignment_requested
            and new_franchise_id is None
            and role in {UserRole.FRANCHISE_OWNER, UserRole.EMPLOYEE}
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'{role.value} must belong to a franchise',
            )

        if updates.get('is_active') is False and role == UserRole.SYSTEM_ADMIN:
            remaining = self.repo.count_active_admins(exclude_id=user_id)
            if remaining < 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Cannot deactivate the last active system admin',
                )

        if reassignment_requested and new_franchise_id is not None and role == UserRole.FRANCHISE_OWNER:
            if str(existing.get('franchise_id')) != str(new_franchise_id):
                if not existing.get('is_active', False) and updates.get('is_active') is not True:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='Only an active franchise owner can be reassigned',
                    )
                self._reassign_owner(user_id, new_franchise_id)
                existing = self.repo.get_profile(user_id) or existing

        if reassignment_requested and new_franchise_id is not None and role == UserRole.EMPLOYEE:
            if str(existing.get('franchise_id')) != str(new_franchise_id):
                self._assert_employee_capacity(new_franchise_id, exclude_id=user_id)
                updates['franchise_id'] = str(new_franchise_id)

        if updates.get('is_active') is True and role == UserRole.EMPLOYEE:
            target_franchise = updates.get('franchise_id') or existing.get('franchise_id')
            if target_franchise:
                self._assert_employee_capacity(UUID(str(target_franchise)), exclude_id=user_id)

        if updates:
            try:
                existing = self.repo.update_profile(user_id, updates)
            except Exception as exc:
                self._raise_profile_write_error(exc, action='update')

        return self.get_user(user_id)

    def reset_password(self, user_id: UUID, *, allow_employee: bool = False) -> PasswordResetResponse:
        row = self.repo.get_profile(user_id) if allow_employee else self._admin_managed_profile(user_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
        email = self.repo.get_auth_email(str(user_id))
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Unable to reset password: auth email not found',
            )
        send_password_recovery_email(self.repo, email=email)
        return PasswordResetResponse(
            password_setup='recovery_email_sent',
            message=f'A password recovery email was sent to {email}.',
        )

    def list_employees(self, owner: CurrentProfile) -> EmployeeListResponse:
        franchise_id = self._owner_franchise_id(owner)
        franchise = self.repo.get_franchise(franchise_id)
        if not franchise:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        rows = self.repo.list_profiles(role=UserRole.EMPLOYEE.value, franchise_id=franchise_id)
        items = self._hydrate(rows)
        from app.modules.employee_sessions.service import EmployeeSessionsService

        logged_in_ids = EmployeeSessionsService().logged_in_employee_ids()
        items = [
            item.model_copy(update={'is_logged_in': str(item.id) in logged_in_ids})
            for item in items
        ]
        active_count = sum(1 for item in items if item.is_active)
        return EmployeeListResponse(
            items=items,
            total=len(items),
            active_count=active_count,
            employee_limit=int(franchise.get('employee_limit') or 10),
        )

    def get_employee(self, owner: CurrentProfile, employee_id: UUID) -> ManagedUser:
        row = self._employee_in_owner_franchise(owner, employee_id)
        return self._hydrate([row])[0]

    def create_employee(self, owner: CurrentProfile, data: EmployeeCreate) -> UserCreateResponse:
        franchise_id = self._owner_franchise_id(owner)
        return self._create_employee(
            franchise_id,
            data.full_name,
            data.login_id,
            data.password,
            data.phone,
        )

    def update_employee(
        self,
        owner: CurrentProfile,
        employee_id: UUID,
        data: EmployeeUpdate,
    ) -> ManagedUser:
        existing = self._employee_in_owner_franchise(owner, employee_id)
        updates = data.model_dump(exclude_unset=True)
        if 'login_id' in updates:
            new_login_id = updates['login_id']
            current_login_id = existing.get('login_id')
            if current_login_id and str(current_login_id) == new_login_id:
                updates.pop('login_id')
            else:
                conflict = self.repo.get_profile_by_login_id(new_login_id)
                if conflict and str(conflict.get('id')) != str(employee_id):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail='User ID is already in use',
                    )
        if updates.get('is_active') is True:
            self._assert_employee_capacity(
                UUID(str(existing['franchise_id'])),
                exclude_id=employee_id,
            )
        if not updates:
            return self._hydrate([existing])[0]
        try:
            updated = self.repo.update_profile(employee_id, updates)
        except Exception as exc:
            self._raise_profile_write_error(exc, action='update')
        return self._hydrate([updated])[0]

    def reset_employee_password(
        self,
        owner: CurrentProfile,
        employee_id: UUID,
        data: EmployeePasswordResetRequest,
    ) -> PasswordResetResponse:
        self._employee_in_owner_franchise(owner, employee_id)
        try:
            self.repo.update_auth_password(str(employee_id), data.new_password)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to reset employee password',
            ) from exc
        return PasswordResetResponse(
            password_setup='password_set',
            message='Employee password updated. Share the new password with the employee offline.',
        )

    def change_own_password(self, profile: CurrentProfile, new_password: str) -> None:
        try:
            self.repo.update_auth_password(str(profile.id), new_password)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Unable to update password',
            ) from exc

    def _create_system_admin(
        self,
        full_name: str,
        email: str,
        phone: str | None,
    ) -> UserCreateResponse:
        provisioned = self._provision_auth_user(email, full_name)
        try:
            profile = self.repo.create_profile(
                {
                    'id': provisioned.auth_user_id,
                    'full_name': full_name,
                    'role': UserRole.SYSTEM_ADMIN.value,
                    'franchise_id': None,
                    'phone': phone,
                    'is_active': True,
                }
            )
        except Exception as exc:
            self._rollback_auth_user(provisioned.auth_user_id)
            self._raise_profile_write_error(exc, action='create')
        return UserCreateResponse(
            user=self._hydrate([profile], fallback_email=email)[0],
            password_setup=provisioned.password_setup,
            message=provisioned.message,
        )

    def _create_employee(
        self,
        franchise_id: UUID,
        full_name: str,
        login_id: str,
        password: str,
        phone: str | None,
    ) -> UserCreateResponse:
        if not self.repo.get_franchise(franchise_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')
        self._assert_employee_capacity(franchise_id)
        if self.repo.get_profile_by_login_id(login_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='User ID is already in use',
            )

        internal_email = employee_auth_identity(login_id)
        if self.repo.find_auth_user_id_by_email(internal_email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='User ID is already in use',
            )

        created_id: str | None = None
        try:
            created = self.repo.create_auth_user_with_temp_password(
                email=internal_email,
                full_name=full_name,
                password=password,
            )
            created_id = _extract_user_id(created) or self.repo.find_auth_user_id_by_email(
                internal_email
            )
            if not created_id:
                raise RuntimeError('Auth user creation did not return an id')
            profile = self.repo.create_profile(
                {
                    'id': created_id,
                    'full_name': full_name,
                    'role': UserRole.EMPLOYEE.value,
                    'franchise_id': str(franchise_id),
                    'phone': phone,
                    'login_id': login_id,
                    'is_active': True,
                }
            )
        except HTTPException:
            if created_id:
                self._rollback_auth_user(created_id)
            raise
        except Exception as exc:
            if created_id:
                self._rollback_auth_user(created_id)
            self._raise_profile_write_error(exc, action='create')
        return UserCreateResponse(
            user=self._hydrate([profile])[0],
            password_setup='password_set',
            message='Employee created. Share the User ID and password with the employee offline.',
        )

    def _provision_auth_user(self, email: str, full_name: str) -> AuthProvisionResult:
        return provision_auth_user(self.repo, email=email, full_name=full_name)

    def _rollback_auth_user(self, auth_user_id: str) -> None:
        try:
            self.repo.delete_auth_user(auth_user_id)
        except Exception:
            pass

    def _reassign_owner(self, user_id: UUID, new_franchise_id: UUID) -> None:
        """Move an active owner to another franchise without creating a second active owner.

        Previous active owner of the target franchise is deactivated first. The existing
        unique index remains the authority for one active owner per franchise.
        """
        if not self.repo.get_franchise(new_franchise_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')

        previous = self.repo.list_profiles(
            role=UserRole.FRANCHISE_OWNER.value,
            franchise_id=new_franchise_id,
            is_active=True,
        )
        for row in previous:
            if str(row.get('id')) != str(user_id):
                try:
                    self.repo.update_profile(UUID(str(row['id'])), {'is_active': False})
                except Exception as exc:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail='Unable to reassign previous franchise owner',
                    ) from exc

        try:
            self.repo.update_profile(
                user_id,
                {
                    'role': UserRole.FRANCHISE_OWNER.value,
                    'franchise_id': str(new_franchise_id),
                    'is_active': True,
                },
            )
        except Exception as exc:
            self._raise_profile_write_error(exc, action='update')

        email = self.repo.get_auth_email(str(user_id))
        if email:
            try:
                self.repo.update_franchise_owner_email(new_franchise_id, email)
            except Exception:
                pass

    def _assert_employee_capacity(
        self,
        franchise_id: UUID,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        franchise = self.repo.get_franchise(franchise_id)
        if not franchise:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Franchise not found')
        limit = int(franchise.get('employee_limit') or 10)
        active = self.repo.count_active_employees(franchise_id, exclude_id=exclude_id)
        if active >= limit:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'Maximum of {limit} active employees allowed per franchise',
            )

    def _admin_managed_profile(self, user_id: UUID) -> dict:
        row = self.repo.get_profile(user_id)
        if not row or row.get('role') == UserRole.EMPLOYEE.value:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
        return row

    def _owner_franchise_id(self, owner: CurrentProfile) -> UUID:
        if owner.franchise_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Franchise owner profile must belong to a franchise',
            )
        return owner.franchise_id

    def _employee_in_owner_franchise(self, owner: CurrentProfile, employee_id: UUID) -> dict:
        franchise_id = self._owner_franchise_id(owner)
        row = self.repo.get_profile(employee_id)
        if not row or row.get('role') != UserRole.EMPLOYEE.value:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Employee not found')
        if str(row.get('franchise_id')) != str(franchise_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Access to this employee is not allowed',
            )
        return row

    def _hydrate(
        self,
        rows: list[dict],
        *,
        fallback_email: str | None = None,
    ) -> list[ManagedUser]:
        if not rows:
            return []
        emails = self.repo.list_auth_emails()
        franchise_ids = [str(row['franchise_id']) for row in rows if row.get('franchise_id')]
        names = self.repo.franchise_name_map(franchise_ids)
        items: list[ManagedUser] = []
        for row in rows:
            user_id = str(row['id'])
            franchise_raw = row.get('franchise_id')
            role = UserRole(row['role'])
            email = emails.get(user_id)
            if not email and (len(rows) == 1 or role != UserRole.EMPLOYEE):
                email = self.repo.get_auth_email(user_id) or (
                    fallback_email if len(rows) == 1 else None
                )
            if role == UserRole.EMPLOYEE or is_internal_employee_identity(email):
                email = None
            items.append(
                ManagedUser(
                    id=row['id'],
                    full_name=row['full_name'],
                    email=email,
                    login_id=row.get('login_id'),
                    phone=row.get('phone'),
                    role=role,
                    franchise_id=franchise_raw,
                    franchise_name=names.get(str(franchise_raw)) if franchise_raw else None,
                    is_active=bool(row.get('is_active', True)),
                    created_at=row.get('created_at'),
                    updated_at=row.get('updated_at'),
                )
            )
        return items

    def _raise_profile_write_error(self, exc: Exception, *, action: str) -> None:
        if self.repo.is_employee_limit_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc) if 'Maximum of' in str(exc) else 'Maximum of 10 active employees allowed per franchise',
            ) from exc
        if self.repo.is_login_id_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='User ID is already in use',
            ) from exc
        if self.repo.is_unique_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Franchise already has an active owner or profile conflict',
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unable to {action} user profile',
        ) from exc
