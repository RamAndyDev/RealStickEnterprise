from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status

SELLING_PRICE_NOT_POSITIVE = 'Selling price must be greater than 0.'
SELLING_PRICE_EXCEEDS_MASTER = 'Selling price must not exceed the master price.'
MASTER_PRICE_CONFLICT = 'Master price cannot be reduced below existing franchise selling prices.'
OWNER_PRICE_INACTIVE_PRODUCT = (
    'Selling price can only be edited when the product is active.'
)
OWNER_PRICE_INACTIVE_ASSIGNMENT = (
    'Selling price can only be edited when the franchise assignment is active.'
)


def as_money(value: object) -> Decimal:
    return Decimal(str(value))


def validate_selling_price(selling_price: object, master_price: object) -> None:
    selling = as_money(selling_price)
    master = as_money(master_price)
    if selling <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=SELLING_PRICE_NOT_POSITIVE,
        )
    if selling > master:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=SELLING_PRICE_EXCEEDS_MASTER,
        )


def selling_price_conflicts_with_master(selling_prices: list[object], master_price: object) -> bool:
    master = as_money(master_price)
    return any(as_money(price) > master for price in selling_prices)


def owner_can_edit_selling_price(product: dict, assignment: dict) -> bool:
    return bool(product.get('is_active')) and bool(assignment.get('is_active'))


def assert_owner_may_edit_selling_price(product: dict, assignment: dict) -> None:
    """Franchise Owner may change selling_price only for an active product + assignment."""
    if not product.get('is_active'):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=OWNER_PRICE_INACTIVE_PRODUCT,
        )
    if not assignment.get('is_active'):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=OWNER_PRICE_INACTIVE_ASSIGNMENT,
        )
