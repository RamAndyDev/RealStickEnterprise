"""In-memory Supabase stand-in for franchise admin tests."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FakeResult:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


def _ilike_match(value: Any, pattern: str) -> bool:
    text = '' if value is None else str(value)
    regex: list[str] = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == '\\' and i + 1 < len(pattern):
            regex.append(re.escape(pattern[i + 1]))
            i += 2
            continue
        if ch == '%':
            regex.append('.*')
        elif ch == '_':
            regex.append('.')
        else:
            regex.append(re.escape(ch))
        i += 1
    return re.fullmatch(''.join(regex), text, flags=re.IGNORECASE) is not None


def _cmp_value(value: Any) -> str:
    return '' if value is None else str(value)


class FakeQuery:
    def __init__(self, db: 'FakeDatabase', table: str):
        self._db = db
        self._table = table
        self._filters: list[tuple[str, str, Any]] = []
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._range: tuple[int, int] | None = None
        self._count_mode: str | None = None
        self._action = 'select'
        self._payload: Any = None
        self._select_cols: str | None = None

    def select(self, *_args, **_kwargs):
        self._action = 'select'
        self._select_cols = _args[0] if _args else '*'
        self._count_mode = _kwargs.get('count')
        return self

    def insert(self, payload):
        self._action = 'insert'
        self._payload = payload
        return self

    def update(self, payload):
        self._action = 'update'
        self._payload = payload
        return self

    def delete(self):
        self._action = 'delete'
        return self

    def eq(self, column, value):
        self._filters.append(('eq', column, value))
        return self

    def neq(self, column, value):
        self._filters.append(('neq', column, value))
        return self

    def gt(self, column, value):
        self._filters.append(('gt', column, value))
        return self

    def gte(self, column, value):
        self._filters.append(('gte', column, value))
        return self

    def lt(self, column, value):
        self._filters.append(('lt', column, value))
        return self

    def lte(self, column, value):
        self._filters.append(('lte', column, value))
        return self

    def ilike(self, column, pattern):
        self._filters.append(('ilike', column, pattern))
        return self

    def in_(self, column, values):
        self._in_filters.append((column, list(values)))
        return self

    def order(self, column, desc=False):
        self._order = (column, bool(desc))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, start, end):
        self._range = (int(start), int(end))
        return self

    def _apply_filters(self, rows: list[dict]) -> list[dict]:
        result = rows
        for op, column, value in self._filters:
            if op == 'eq':
                result = [r for r in result if str(r.get(column)) == str(value)]
            elif op == 'neq':
                result = [r for r in result if str(r.get(column)) != str(value)]
            elif op == 'gt':
                result = [
                    r for r in result
                    if r.get(column) is not None and _cmp_value(r.get(column)) > _cmp_value(value)
                ]
            elif op == 'gte':
                result = [
                    r for r in result
                    if r.get(column) is not None and _cmp_value(r.get(column)) >= _cmp_value(value)
                ]
            elif op == 'lt':
                result = [
                    r for r in result
                    if r.get(column) is not None and _cmp_value(r.get(column)) < _cmp_value(value)
                ]
            elif op == 'lte':
                result = [
                    r for r in result
                    if r.get(column) is not None and _cmp_value(r.get(column)) <= _cmp_value(value)
                ]
            elif op == 'ilike':
                result = [r for r in result if _ilike_match(r.get(column), str(value))]
        for column, values in self._in_filters:
            allowed = {str(v) for v in values}
            result = [r for r in result if str(r.get(column)) in allowed]
        return result

    def execute(self):
        table_rows = self._db.tables.setdefault(self._table, [])

        with self._db.lock:
            return self._execute_locked(table_rows)

    def _execute_locked(self, table_rows: list[dict]):

        if self._action == 'insert':
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            created = []
            for raw in payloads:
                row = deepcopy(raw)
                row.setdefault('id', str(uuid4()))
                row.setdefault('created_at', _now())
                row.setdefault('updated_at', _now())
                if self._table == 'franchises':
                    row.setdefault('settings', {})
                    row.setdefault('is_archived', False)
                    row.setdefault('employee_limit', 10)
                    # Unique code check
                    if row.get('code'):
                        for existing in table_rows:
                            if existing.get('code') == row['code']:
                                raise Exception('duplicate key value violates unique constraint')
                if self._table == 'profiles':
                    self._db.enforce_profile_rules(table_rows, row, current_row=None)
                    # one active owner per franchise
                    if (
                        row.get('role') == 'FRANCHISE_OWNER'
                        and row.get('is_active')
                        and row.get('franchise_id')
                    ):
                        for existing in table_rows:
                            if (
                                existing.get('role') == 'FRANCHISE_OWNER'
                                and existing.get('is_active')
                                and str(existing.get('franchise_id')) == str(row.get('franchise_id'))
                                and str(existing.get('id')) != str(row.get('id'))
                            ):
                                raise Exception('duplicate key value violates unique constraint')
                if self._table == 'launch_checklist_items':
                    for existing in table_rows:
                        if (
                            str(existing.get('franchise_id')) == str(row.get('franchise_id'))
                            and existing.get('item_key') == row.get('item_key')
                        ):
                            raise Exception('duplicate key value violates unique constraint')
                if self._table == 'product_categories':
                    row.setdefault('display_order', 0)
                    row.setdefault('is_active', True)
                    new_name = (row.get('name') or '').strip().lower()
                    for existing in table_rows:
                        if (existing.get('name') or '').strip().lower() == new_name:
                            raise Exception('duplicate key value violates unique constraint')
                if self._table == 'products':
                    row.setdefault('is_active', True)
                    row.setdefault('metadata', {})
                    if row.get('sku'):
                        for existing in table_rows:
                            if existing.get('sku') == row.get('sku'):
                                raise Exception('duplicate key value violates unique constraint')
                if self._table == 'franchise_product_prices':
                    row.setdefault('is_active', True)
                    self._db.enforce_selling_price(row)
                    for existing in table_rows:
                        if (
                            str(existing.get('franchise_id')) == str(row.get('franchise_id'))
                            and str(existing.get('product_id')) == str(row.get('product_id'))
                        ):
                            raise Exception('duplicate key value violates unique constraint')
                if self._table == 'system_settings':
                    if not row.get('key'):
                        raise Exception('system_settings.key is required')
                    for existing in table_rows:
                        if existing.get('key') == row.get('key'):
                            raise Exception('duplicate key value violates unique constraint')
                if self._table == 'gst_settings':
                    row.setdefault('is_active', True)
                    if row.get('is_active'):
                        for existing in table_rows:
                            if existing.get('is_active'):
                                raise Exception('duplicate key value violates unique constraint')
                if self._table == 'discounts':
                    row.setdefault('discount_type', 'PERCENTAGE')
                    row.setdefault('is_active', True)
                    row.setdefault('description', None)
                    row.setdefault('valid_from', None)
                    row.setdefault('valid_to', None)
                    row.setdefault('franchise_id', None)
                    row.setdefault('promotion_id', None)
                if self._table == 'promotions':
                    row.setdefault('is_active', True)
                    row.setdefault('description', None)
                    row.setdefault('valid_from', None)
                    row.setdefault('valid_to', None)
                    code = (row.get('promo_code') or '').strip().lower()
                    for existing in table_rows:
                        if (existing.get('promo_code') or '').strip().lower() == code:
                            raise Exception('duplicate key value violates unique constraint')
                if self._table == 'promotion_franchises':
                    for existing in table_rows:
                        if (
                            str(existing.get('promotion_id')) == str(row.get('promotion_id'))
                            and str(existing.get('franchise_id')) == str(row.get('franchise_id'))
                        ):
                            raise Exception('duplicate key value violates unique constraint')
                if self._table == 'profiles' and row.get('login_id'):
                    needle = str(row['login_id']).strip().lower()
                    for existing in table_rows:
                        existing_login = str(existing.get('login_id') or '').strip().lower()
                        if existing_login and existing_login == needle:
                            raise Exception(
                                'duplicate key value violates unique constraint on login_id'
                            )
                if self._table == 'orders':
                    row.setdefault('status', 'DRAFT')
                    row.setdefault('subtotal', 0)
                    row.setdefault('discount_amount', 0)
                    row.setdefault('taxable_amount', 0)
                    row.setdefault('gst_rate', 0)
                    row.setdefault('gst_amount', 0)
                    row.setdefault('cgst_rate', 0)
                    row.setdefault('sgst_rate', 0)
                    row.setdefault('cgst_amount', 0)
                    row.setdefault('sgst_amount', 0)
                    row.setdefault('total_amount', 0)
                    for existing in table_rows:
                        if (
                            str(existing.get('franchise_id')) == str(row.get('franchise_id'))
                            and existing.get('bill_number') == row.get('bill_number')
                        ):
                            raise Exception('duplicate key value violates unique constraint')
                    status = row.get('status')
                    if status == 'COMPLETED' and (
                        not row.get('payment_method') or not row.get('completed_at')
                    ):
                        raise Exception('orders_completed_requires_payment_check')
                    if status == 'CANCELLED' and not row.get('cancelled_at'):
                        raise Exception('orders_completed_requires_payment_check')
                if self._table == 'gallery_items':
                    row.setdefault('display_order', 0)
                    row.setdefault('is_approved', False)
                    row.setdefault('is_archived', False)
                    row.setdefault('franchise_id', None)
                    row.setdefault('title', None)
                    row.setdefault('caption', None)
                    row.setdefault('author_name', None)
                    row.setdefault('storage_path', None)
                    row.setdefault('media_url', None)
                if self._table == 'franchise_audit_items':
                    for existing in table_rows:
                        if (
                            str(existing.get('audit_id')) == str(row.get('audit_id'))
                            and existing.get('item_key') == row.get('item_key')
                        ):
                            raise Exception('duplicate key value violates unique constraint')
                table_rows.append(row)
                created.append(deepcopy(row))
            return FakeResult(created)

        if self._action == 'update':
            matched = self._apply_filters(table_rows)
            updated = []
            for row in matched:
                # unique owner constraint on profile update
                if self._table == 'profiles':
                    next_row = {**row, **deepcopy(self._payload), 'updated_at': _now()}
                    self._db.enforce_profile_rules(table_rows, next_row, current_row=row)
                    if (
                        next_row.get('role') == 'FRANCHISE_OWNER'
                        and next_row.get('is_active')
                        and next_row.get('franchise_id')
                    ):
                        for existing in table_rows:
                            if (
                                existing is not row
                                and existing.get('role') == 'FRANCHISE_OWNER'
                                and existing.get('is_active')
                                and str(existing.get('franchise_id'))
                                == str(next_row.get('franchise_id'))
                            ):
                                raise Exception('duplicate key value violates unique constraint')
                    row.clear()
                    row.update(next_row)
                else:
                    if self._table == 'franchises' and self._payload.get('code'):
                        for existing in table_rows:
                            if (
                                existing is not row
                                and existing.get('code') == self._payload.get('code')
                            ):
                                raise Exception('duplicate key value violates unique constraint')
                    if self._table == 'product_categories' and self._payload.get('name'):
                        new_name = (self._payload.get('name') or '').strip().lower()
                        for existing in table_rows:
                            if (
                                existing is not row
                                and (existing.get('name') or '').strip().lower() == new_name
                            ):
                                raise Exception('duplicate key value violates unique constraint')
                    if self._table == 'products' and self._payload.get('sku'):
                        for existing in table_rows:
                            if (
                                existing is not row
                                and existing.get('sku') == self._payload.get('sku')
                            ):
                                raise Exception('duplicate key value violates unique constraint')
                    next_row = {**row, **deepcopy(self._payload), 'updated_at': _now()}
                    if self._table == 'products' and 'price' in self._payload:
                        self._db.enforce_master_price(next_row)
                    if self._table == 'franchise_product_prices' and (
                        'selling_price' in self._payload or 'product_id' in self._payload
                    ):
                        self._db.enforce_selling_price(next_row)
                    row.clear()
                    row.update(next_row)
                updated.append(deepcopy(row))
            return FakeResult(updated)

        if self._action == 'delete':
            matched = self._apply_filters(table_rows)
            if self._table == 'products':
                self._db.enforce_product_delete_fks(matched)
            deleted = [deepcopy(r) for r in matched]
            ids = {str(r.get('id')) for r in matched}
            self._db.tables[self._table] = [
                r for r in table_rows if str(r.get('id')) not in ids
            ]
            if self._table == 'franchise_audits' and ids:
                self._db.tables['franchise_audit_items'] = [
                    row
                    for row in self._db.tables.get('franchise_audit_items', [])
                    if str(row.get('audit_id')) not in ids
                ]
            return FakeResult(deleted)

        # select
        rows = [deepcopy(r) for r in self._apply_filters(table_rows)]
        if self._order:
            column, desc = self._order
            rows.sort(key=lambda r: r.get(column) or '', reverse=desc)
        total = len(rows)
        if self._range is not None:
            start, end = self._range
            rows = rows[start:end + 1]
        elif self._limit is not None:
            rows = rows[: self._limit]
        count = total if self._count_mode else None
        return FakeResult(rows, count=count)


class FakeAuthAdmin:
    def __init__(self, users: list[Any]):
        self._users = users
        self.invites: list[dict[str, Any]] = []
        self.recovery_links: list[dict[str, Any]] = []
        self.fail_next_invite = False

    def list_users(self, page: int = 1, per_page: int = 200):
        start = (page - 1) * per_page
        end = start + per_page

        class _Resp:
            def __init__(self, users):
                self.users = users

        return _Resp(self._users[start:end])

    def _ensure_unique_email(self, email: str) -> None:
        normalized = email.strip().lower()
        for user in self._users:
            if (getattr(user, 'email', '') or '').strip().lower() == normalized:
                raise Exception('User already registered')

    def invite_user_by_email(self, email: str, options: dict | None = None):
        if self.fail_next_invite:
            self.fail_next_invite = False
            raise Exception('Unable to send invite email')
        self._ensure_unique_email(email)
        from types import SimpleNamespace
        from uuid import uuid4

        user = SimpleNamespace(id=str(uuid4()), email=email.strip().lower())
        self._users.append(user)
        self.invites.append({'email': email, 'options': options or {}})
        return SimpleNamespace(user=user)

    def create_user(self, attributes: dict):
        email = attributes['email']
        self._ensure_unique_email(email)
        from types import SimpleNamespace
        from uuid import uuid4

        user = SimpleNamespace(
            id=str(uuid4()),
            email=email.strip().lower(),
            password=attributes.get('password'),
        )
        self._users.append(user)
        return SimpleNamespace(user=user)

    def generate_link(self, params: dict):
        from types import SimpleNamespace

        self.recovery_links.append(params)
        return SimpleNamespace(
            properties=SimpleNamespace(action_link='https://example.supabase.co/auth/v1/verify?type=recovery')
        )

    def delete_user(self, user_id: str):
        self._users[:] = [u for u in self._users if str(u.id) != str(user_id)]

    def get_user_by_id(self, user_id: str):
        from types import SimpleNamespace

        for user in self._users:
            if str(user.id) == str(user_id):
                return SimpleNamespace(user=user)
        raise Exception('User not found')

    def update_user_by_id(self, user_id: str, attributes: dict):
        from types import SimpleNamespace

        for user in self._users:
            if str(user.id) == str(user_id):
                if 'password' in attributes:
                    setattr(user, 'password', attributes['password'])
                if 'email' in attributes:
                    user.email = attributes['email']
                return SimpleNamespace(user=user)
        raise Exception('User not found')


class FakeAuth:
    def __init__(self, users: list[Any]):
        self.admin = FakeAuthAdmin(users)
        self.recovery_emails: list[dict[str, Any]] = []

    def reset_password_for_email(self, email: str, options: dict | None = None):
        self.recovery_emails.append({'email': email.strip().lower(), 'options': options or {}})

    def sign_in_with_password(self, email: str, password: str) -> dict[str, Any]:
        needle = email.strip().lower()
        for user in self.admin._users:
            if (getattr(user, 'email', '') or '').strip().lower() != needle:
                continue
            if getattr(user, 'password', None) != password:
                raise Exception('Invalid login credentials')
            return {
                'access_token': f'fake-access-{user.id}',
                'refresh_token': f'fake-refresh-{user.id}',
                'token_type': 'bearer',
                'expires_in': 3600,
            }
        raise Exception('Invalid login credentials')


class FakeStorageBucket:
    def __init__(self, db: 'FakeDatabase', bucket: str):
        self._db = db
        self._bucket = bucket

    def upload(self, path: str, content: bytes, file_options: dict | None = None):
        if getattr(self._db, 'fail_next_storage_upload', False):
            self._db.fail_next_storage_upload = False
            raise Exception('storage upload failed')
        self._db.storage_objects[(self._bucket, path)] = {
            'content': content,
            'options': file_options or {},
        }
        return {'path': path}

    def remove(self, paths: list[str]):
        for path in paths:
            self._db.storage_objects.pop((self._bucket, path), None)
        return [{'name': p} for p in paths]

    def get_public_url(self, path: str) -> str:
        return f'https://example.supabase.co/storage/v1/object/public/{self._bucket}/{path}'


class FakeStorage:
    def __init__(self, db: 'FakeDatabase'):
        self._db = db
        self.buckets = {'gallery'}

    def from_(self, bucket: str) -> FakeStorageBucket:
        return FakeStorageBucket(self._db, bucket)

    def get_bucket(self, name: str) -> dict[str, str]:
        if name not in self.buckets:
            raise Exception('Bucket not found')
        return {'id': name}

    def create_bucket(self, name: str, options: dict | None = None) -> dict[str, str]:
        self.buckets.add(name)
        self._db.created_buckets.append({'id': name, 'options': options or {}})
        return {'id': name}


class FakeDatabase:
    def __init__(
        self,
        *,
        profiles: list[dict] | None = None,
        franchises: list[dict] | None = None,
        applications: list[dict] | None = None,
        payments: list[dict] | None = None,
        checklist: list[dict] | None = None,
        product_categories: list[dict] | None = None,
        products: list[dict] | None = None,
        franchise_product_prices: list[dict] | None = None,
        gst_settings: list[dict] | None = None,
        system_settings: list[dict] | None = None,
        discounts: list[dict] | None = None,
        orders: list[dict] | None = None,
        order_items: list[dict] | None = None,
        gallery_items: list[dict] | None = None,
        promotions: list[dict] | None = None,
        promotion_franchises: list[dict] | None = None,
        franchise_audits: list[dict] | None = None,
        franchise_audit_items: list[dict] | None = None,
        employee_sessions: list[dict] | None = None,
        recipes: list[dict] | None = None,
        recipe_items: list[dict] | None = None,
        inventory_movements: list[dict] | None = None,
        auth_users: list[Any] | None = None,
    ):
        self.tables: dict[str, list[dict]] = {
            'profiles': deepcopy(profiles or []),
            'franchises': deepcopy(franchises or []),
            'franchise_applications': deepcopy(applications or []),
            'franchise_payments': deepcopy(payments or []),
            'launch_checklist_items': deepcopy(checklist or []),
            'product_categories': deepcopy(product_categories or []),
            'products': deepcopy(products or []),
            'franchise_product_prices': deepcopy(franchise_product_prices or []),
            'gst_settings': deepcopy(gst_settings or []),
            'system_settings': deepcopy(system_settings or []),
            'discounts': deepcopy(discounts or []),
            'orders': deepcopy(orders or []),
            'order_items': deepcopy(order_items or []),
            'gallery_items': deepcopy(gallery_items or []),
            'promotions': deepcopy(promotions or []),
            'promotion_franchises': deepcopy(promotion_franchises or []),
            'franchise_audits': deepcopy(franchise_audits or []),
            'franchise_audit_items': deepcopy(franchise_audit_items or []),
            'employee_sessions': deepcopy(employee_sessions or []),
            'recipes': deepcopy(recipes or []),
            'recipe_items': deepcopy(recipe_items or []),
            'inventory_movements': deepcopy(inventory_movements or []),
        }
        self.auth = FakeAuth(auth_users or [])
        self.storage_objects: dict[tuple[str, str], dict] = {}
        self.storage = FakeStorage(self)
        self.created_buckets: list[dict[str, Any]] = []
        self.lock = RLock()
        self.fail_next_set_category_active = False
        self.fail_next_storage_upload = False

    def sign_in_with_password(self, email: str, password: str) -> dict[str, Any]:
        return self.auth.sign_in_with_password(email, password)

    def enforce_selling_price(self, row: dict) -> None:
        selling = row.get('selling_price')
        if selling is None or float(selling) <= 0:
            raise Exception('Selling price must be greater than 0')

    def enforce_master_price(self, product_row: dict) -> None:
        # Master price is independent of franchise selling prices.
        return

    def enforce_product_delete_fks(self, products: list[dict]) -> None:
        """Mirror Postgres NO ACTION FKs on products.id. No CASCADE."""
        product_ids = {str(row.get('id')) for row in products if row.get('id')}
        if not product_ids:
            return
        for table, column in (
            ('franchise_product_prices', 'product_id'),
            ('order_items', 'product_id'),
            ('recipes', 'product_id'),
        ):
            for row in self.tables.get(table, []):
                if str(row.get(column) or '') in product_ids:
                    raise Exception(
                        'update or delete on table "products" violates foreign key constraint'
                    )

    def enforce_profile_rules(
        self,
        table_rows: list[dict],
        next_row: dict,
        *,
        current_row: dict | None,
    ) -> None:
        role = next_row.get('role')
        if role == 'SYSTEM_ADMIN' and next_row.get('franchise_id'):
            raise Exception('SYSTEM_ADMIN profiles must not belong to a franchise')
        if role in {'FRANCHISE_OWNER', 'EMPLOYEE'} and not next_row.get('franchise_id'):
            raise Exception(f'{role} profiles must belong to a franchise')

        login_id = next_row.get('login_id')
        if login_id:
            needle = str(login_id).strip().lower()
            for existing in table_rows:
                if existing is current_row:
                    continue
                existing_login = str(existing.get('login_id') or '').strip().lower()
                if existing_login and existing_login == needle:
                    raise Exception(
                        'duplicate key value violates unique constraint on login_id'
                    )

        if role != 'EMPLOYEE' or not next_row.get('is_active'):
            return

        franchise_id = next_row.get('franchise_id')
        franchise = next(
            (
                row
                for row in self.tables.get('franchises', [])
                if str(row.get('id')) == str(franchise_id)
            ),
            None,
        )
        if not franchise:
            raise Exception('Franchise not found for employee profile')
        max_employees = int(franchise.get('employee_limit') or 10)
        count = 0
        for existing in table_rows:
            if existing is current_row:
                continue
            if (
                str(existing.get('franchise_id')) == str(franchise_id)
                and existing.get('role') == 'EMPLOYEE'
                and existing.get('is_active')
            ):
                count += 1
        if count >= max_employees:
            raise Exception(f'Maximum of {max_employees} active employees allowed per franchise')

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)

    def rpc(self, fn: str, params: dict | None = None, **_kwargs) -> 'FakeRpc':
        return FakeRpc(self, fn, params or {})


class FakeRpc:
    def __init__(self, db: FakeDatabase, fn: str, params: dict):
        self._db = db
        self._fn = fn
        self._params = params

    def execute(self):
        from app.modules.pos.engine import PosCheckoutError, complete_pos_order_atomic
        from app.modules.products.category_ops import (
            CategoryOpsError,
            set_product_category_active_atomic,
        )

        if self._fn == 'set_product_category_active':
            with self._db.lock:
                if self._db.fail_next_set_category_active:
                    self._db.fail_next_set_category_active = False
                    raise Exception('simulated category deactivation failure')
                try:
                    data = set_product_category_active_atomic(
                        self._db.tables,
                        self._params.get('p_category_id'),
                        bool(self._params.get('p_is_active')),
                    )
                except CategoryOpsError as exc:
                    raise Exception('CATEGORY_NOT_FOUND' if exc.code == 'NOT_FOUND' else str(exc)) from exc
                return FakeResult(data)

        if self._fn != 'complete_pos_order':
            raise Exception(f'Unknown rpc {self._fn}')
        with self._db.lock:
            try:
                data = complete_pos_order_atomic(self._db.tables, self._params)
            except PosCheckoutError:
                raise
            except Exception as exc:
                raise PosCheckoutError('CHECKOUT_FAILED', str(exc)) from exc
            return FakeResult(data)
