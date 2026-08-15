"""Product image validation and Supabase Storage helpers."""

from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.modules.products.constants import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    ALLOWED_IMAGE_EXTENSIONS,
    PRODUCT_IMAGE_BUCKET,
    PRODUCT_IMAGE_MAX_BYTES,
)


def detect_image_content_type(data: bytes) -> str | None:
    """Detect image type from magic bytes (do not trust client Content-Type alone)."""
    if len(data) >= 3 and data[0:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if len(data) >= 8 and data[0:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if len(data) >= 12 and data[0:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return None


async def read_and_validate_image(file: UploadFile) -> tuple[bytes, str, str]:
    """
    Read upload, enforce size/type via magic bytes.
    Returns (content, content_type, extension).
    """
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Image file is empty',
        )
    if len(content) > PRODUCT_IMAGE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Image exceeds maximum size of {PRODUCT_IMAGE_MAX_BYTES // (1024 * 1024)} MB',
        )

    detected = detect_image_content_type(content)
    if detected is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Unsupported image type. Allowed: JPG, PNG, WEBP',
        )

    declared = (file.content_type or '').split(';')[0].strip().lower()
    # Accept image/jpg as alias for jpeg when declared, but require magic bytes match JPEG.
    if declared in {'image/jpg', 'image/pjpeg'}:
        declared = 'image/jpeg'
    if declared and declared not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Unsupported image type. Allowed: JPG, PNG, WEBP',
        )
    if declared and declared != detected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Image content does not match declared content type',
        )

    extension = ALLOWED_IMAGE_EXTENSIONS[detected]
    return content, detected, extension


def build_product_image_path(product_id: str, extension: str) -> str:
    return f'{product_id}/{uuid4().hex}.{extension}'


def image_metadata(image_url: str, image_path: str) -> dict[str, str]:
    return {'image_url': image_url, 'image_path': image_path}


def strip_image_metadata(metadata: dict) -> dict:
    cleaned = dict(metadata or {})
    cleaned.pop('image_url', None)
    cleaned.pop('image_path', None)
    cleaned.pop('emoji', None)
    return cleaned


__all__ = [
    'PRODUCT_IMAGE_BUCKET',
    'build_product_image_path',
    'detect_image_content_type',
    'image_metadata',
    'read_and_validate_image',
    'strip_image_metadata',
]
