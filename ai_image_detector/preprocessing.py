"""
preprocessing.py
=================
Image loading and preprocessing.

Responsibilities (requirement #1):
- Accept JPG / JPEG / PNG / WebP.
- Convert safely to RGB.
- Handle different resolutions and aspect ratios.
- Produce a standardized analysis copy (fixed size, for the classifier).
- Preserve the original image object separately for metadata analysis.
- Provide JPEG/compression-aware variants so a single round of social-media
  recompression doesn't automatically push the verdict toward "AI".
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from config import PreprocessConfig

logger = logging.getLogger(__name__)


class UnsupportedImageError(ValueError):
    """Raised when a file is not a supported / decodable image."""


@dataclass
class PreparedImage:
    """Everything downstream feature extractors need."""

    source_path: str | None
    original: Image.Image          # untouched (aside from EXIF-orientation fix), for metadata
    analysis_rgb: np.ndarray        # standardized-size RGB array, float32 [0, 1]
    analysis_pil: Image.Image       # standardized-size PIL image (RGB)
    original_size: tuple[int, int]  # (width, height)
    recompressed_variants: dict[int, np.ndarray]  # quality -> RGB array (compression-aware)


def _load_pil(path_or_bytes: str | Path | bytes) -> Image.Image:
    try:
        if isinstance(path_or_bytes, (str, Path)):
            img = Image.open(path_or_bytes)
        else:
            img = Image.open(io.BytesIO(path_or_bytes))
        img.load()
    except Exception as exc:  # noqa: BLE001 - want to wrap any decode failure
        raise UnsupportedImageError(f"Could not decode image: {exc}") from exc
    return img


def _validate_extension(path: str | Path, cfg: PreprocessConfig) -> None:
    suffix = Path(path).suffix.lower()
    if suffix not in cfg.supported_extensions:
        raise UnsupportedImageError(
            f"Unsupported file extension '{suffix}'. Supported: {cfg.supported_extensions}"
        )


def _to_rgb(img: Image.Image) -> Image.Image:
    """Safely convert any PIL mode (P, RGBA, L, CMYK, ...) to RGB."""
    img = ImageOps.exif_transpose(img)  # fix camera-rotation metadata before resizing
    if img.mode == "RGBA" or img.mode == "LA" or (img.mode == "P" and "transparency" in img.info):
        background = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _jpeg_recompress(img_rgb: Image.Image, quality: int) -> Image.Image:
    """Round-trip through JPEG at a given quality to simulate social-media compression."""
    buf = io.BytesIO()
    img_rgb.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def prepare_image(
    path_or_bytes: str | Path | bytes,
    cfg: PreprocessConfig,
    source_path: str | None = None,
) -> PreparedImage:
    """
    Load + normalize an image for both forensic and deep-feature extraction.

    Raises UnsupportedImageError on decode failure or unsupported extension.
    """
    if isinstance(path_or_bytes, (str, Path)):
        _validate_extension(path_or_bytes, cfg)
        source_path = str(path_or_bytes)

    original = _load_pil(path_or_bytes)
    rgb_full = _to_rgb(original)
    original_size = rgb_full.size  # (w, h)

    analysis_pil = rgb_full.resize(cfg.target_size, Image.BICUBIC)
    analysis_rgb = np.asarray(analysis_pil).astype(np.float32) / 255.0

    recompressed_variants: dict[int, np.ndarray] = {}
    for q in cfg.jpeg_quality_probe_levels:
        try:
            recompressed = _jpeg_recompress(analysis_pil, q)
            recompressed_variants[q] = np.asarray(recompressed).astype(np.float32) / 255.0
        except Exception as exc:  # noqa: BLE001
            logger.warning("JPEG recompression probe at quality=%s failed: %s", q, exc)

    return PreparedImage(
        source_path=source_path,
        original=original,
        analysis_rgb=analysis_rgb,
        analysis_pil=analysis_pil,
        original_size=original_size,
        recompressed_variants=recompressed_variants,
    )


def apply_transform_for_robustness_test(
    prepared: PreparedImage, transform: str, cfg: PreprocessConfig
) -> np.ndarray:
    """
    Produce a transformed analysis array for robustness evaluation
    (requirement #9): jpeg compression, resize, crop, brightness, blur.
    Returns an RGB float32 array in [0, 1] at the standard target size.
    """
    from PIL import ImageEnhance, ImageFilter

    img = prepared.analysis_pil

    if transform == "jpeg_low":
        img = _jpeg_recompress(img, quality=40)
    elif transform == "resize_down_up":
        w, h = img.size
        small = img.resize((max(1, w // 2), max(1, h // 2)), Image.BICUBIC)
        img = small.resize((w, h), Image.BICUBIC)
    elif transform == "crop":
        w, h = img.size
        dx, dy = int(w * 0.05), int(h * 0.05)
        img = img.crop((dx, dy, w - dx, h - dy)).resize((w, h), Image.BICUBIC)
    elif transform == "brightness":
        img = ImageEnhance.Brightness(img).enhance(1.25)
    elif transform == "blur":
        img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
    elif transform == "screenshot_like":
        # Downscale + slight JPEG artifacting + a hair of upscale, mimicking a
        # phone screenshot of an image rendered in a browser/app.
        w, h = img.size
        img = img.resize((int(w * 0.9), int(h * 0.9)), Image.BICUBIC)
        img = _jpeg_recompress(img, quality=80)
        img = img.resize((w, h), Image.BICUBIC)
    else:
        raise ValueError(f"Unknown robustness transform: {transform}")

    img = img.resize(cfg.target_size, Image.BICUBIC)
    return np.asarray(img).astype(np.float32) / 255.0
