from enum import StrEnum


class UserRole(StrEnum):
    SYSTEM_ADMIN = 'SYSTEM_ADMIN'
    FRANCHISE_OWNER = 'FRANCHISE_OWNER'
    EMPLOYEE = 'EMPLOYEE'
