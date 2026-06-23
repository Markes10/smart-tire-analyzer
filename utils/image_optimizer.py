"""
Lossless / near-lossless image compression before storage or inference.

Uses Pillow only (already a project dependency) to strip metadata and
re-encode JPEG/WebP with optimized settings while preserving visual quality.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Literal

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

ContentType = Literal["image/jpeg", "image/png", "image/webp"]

JPEG_QUALITY = 88
WEBP_QUALITY = 85
PNG_OPTIMIZE = True


@dataclass(frozen=True)
class OptimizationResult:
    data: bytes
    content_type: ContentType
    original_bytes: int
    optimized_bytes: int
    savings_ratio: float

    @property
    def saved_bytes(self) -> int:
        return max(0, self.original_bytes - self.optimized_bytes)


def _normalize_content_type(content_type: str | None) -> ContentType:
    normalized = (content_type or "image/jpeg").lower().split(";")[0].strip()
    if normalized in {"image/jpeg", "image/jpg"}:
        return "image/jpeg"
    if normalized == "image/png":
        return "image/png"
    if normalized == "image/webp":
        return "image/webp"
    return "image/jpeg"


def _detect_content_type_from_bytes(image_bytes: bytes, fallback: ContentType) -> ContentType:
    """Best-effort sniffing of encoded bytes to keep metadata and payload aligned."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            format_name = (image.format or "").upper()
    except Exception:
        return fallback

    if format_name == "PNG":
        return "image/png"
    if format_name in {"JPEG", "JPG"}:
        return "image/jpeg"
    if format_name == "WEBP":
        return "image/webp"
    return fallback


def optimize_image_bytes(
    image_bytes: bytes,
    *,
    content_type: str | None = None,
    max_dimension: int = 2048,
    jpeg_quality: int = JPEG_QUALITY,
    webp_quality: int = WEBP_QUALITY,
) -> OptimizationResult:
    """
    Compress image bytes for storage/inference without changing aspect ratio.

    PNG inputs with alpha are preserved as PNG. JPEG/WebP are re-encoded with
    optimized encoder settings and EXIF stripped.
    """
    original_size = len(image_bytes)
    target_type = _normalize_content_type(content_type)

    with Image.open(io.BytesIO(image_bytes)) as opened_image:
        image = ImageOps.exif_transpose(opened_image)
        if max(image.size) > max_dimension:
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        has_alpha = image.mode in {"RGBA", "LA"} or (
            image.mode == "P" and "transparency" in image.info
        )
        output_type: ContentType = "image/png" if has_alpha else target_type

        buffer = io.BytesIO()
        if output_type == "image/png":
            rgb = image.convert("RGBA") if has_alpha else image.convert("RGB")
            rgb.save(buffer, format="PNG", optimize=PNG_OPTIMIZE)
        elif output_type == "image/webp":
            rgb = image.convert("RGB")
            rgb.save(buffer, format="WEBP", quality=webp_quality, method=6)
        else:
            rgb = image.convert("RGB")
            rgb.save(
                buffer,
                format="JPEG",
                quality=jpeg_quality,
                optimize=True,
                progressive=True,
            )

    optimized = buffer.getvalue()
    if len(optimized) >= original_size:
        optimized = image_bytes
        output_type = _detect_content_type_from_bytes(image_bytes, output_type)

    savings = 1.0 - (len(optimized) / original_size) if original_size else 0.0
    logger.debug(
        "Image optimizer: %d -> %d bytes (%.1f%% saved, %s)",
        original_size,
        len(optimized),
        savings * 100,
        output_type,
    )
    return OptimizationResult(
        data=optimized,
        content_type=output_type,
        original_bytes=original_size,
        optimized_bytes=len(optimized),
        savings_ratio=round(savings, 4),
    )
