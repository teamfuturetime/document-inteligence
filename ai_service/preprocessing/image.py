"""Tiền xử lý hình ảnh bằng OpenCV: grayscale, tăng tương phản, khử nhiễu."""
from __future__ import annotations

from typing import Optional

import numpy as np

try:
    import cv2

    _HAS_CV2 = True
except ImportError:  # pragma: no cover
    _HAS_CV2 = False


class PreprocessingError(Exception):
    """Lỗi khi tiền xử lý ảnh thất bại."""


def _require_cv2() -> None:
    if not _HAS_CV2:
        raise PreprocessingError(
            "OpenCV chưa được cài đặt. Chạy: pip install opencv-python-headless"
        )


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Chuyển ảnh màu sang grayscale."""
    _require_cv2()
    if image.ndim == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def enhance_contrast(image: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    """Tăng tương phản bằng CLAHE (phù hợp ảnh scan mờ)."""
    _require_cv2()
    gray = to_grayscale(image)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    return clahe.apply(gray)


def denoise(image: np.ndarray, strength: int = 10) -> np.ndarray:
    """Khử nhiễu bằng Non-local Means Denoising."""
    _require_cv2()
    gray = to_grayscale(image)
    return cv2.fastNlMeansDenoising(gray, None, strength, 7, 21)


def binarize(image: np.ndarray, threshold: int = 0) -> np.ndarray:
    """Chuyển ảnh sang nhị phân (Otsu nếu threshold=0)."""
    _require_cv2()
    gray = to_grayscale(image)
    if threshold > 0:
        _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    else:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def adaptive_binarize(image: np.ndarray) -> np.ndarray:
    """Threshold uneven scans while retaining small Vietnamese diacritics."""

    _require_cv2()
    gray = to_grayscale(image)
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        12,
    )


def sharpen(image: np.ndarray, amount: float = 0.35) -> np.ndarray:
    """Apply a deliberately light unsharp mask to avoid damaging accents."""

    _require_cv2()
    gray = to_grayscale(image)
    blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)
    return cv2.addWeighted(gray, 1.0 + amount, blurred, -amount, 0)


def resize_to_max_width(image: np.ndarray, max_width: int = 2000) -> np.ndarray:
    """Thu nhỏ ảnh nếu vượt quá chiều rộng tối đa (giảm RAM)."""
    _require_cv2()
    h, w = image.shape[:2]
    if w <= max_width:
        return image
    scale = max_width / w
    new_size = (max_width, int(h * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def resize_for_ocr(
    image: np.ndarray,
    *,
    min_width: int = 1200,
    max_width: int = 2400,
    max_upscale: float = 2.0,
    max_pixels: int = 40_000_000,
) -> np.ndarray:
    """Resize proportionally, enlarging only genuinely low-resolution inputs."""

    _require_cv2()
    height, width = image.shape[:2]
    if width <= 0 or height <= 0:
        raise PreprocessingError("Ảnh không có kích thước hợp lệ")
    scale = 1.0
    if width > max_width:
        scale = max_width / width
    elif width < min_width:
        scale = min(min_width / width, max_upscale)
    if height * width * scale * scale > max_pixels:
        scale = min(scale, (max_pixels / (height * width)) ** 0.5)
    if abs(scale - 1.0) < 0.01:
        return image
    interpolation = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    return cv2.resize(
        image,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=interpolation,
    )


def build_preprocessing_candidates(image: np.ndarray) -> list[np.ndarray]:
    """Return a small ordered set of OCR variants, from safest to strongest."""

    normalized = to_grayscale(resize_for_ocr(image))
    enhanced = sharpen(denoise(enhance_contrast(normalized), strength=5))
    thresholded = adaptive_binarize(enhanced)
    return [normalized, enhanced, thresholded]


def preprocess_image(
    image: np.ndarray,
    *,
    grayscale: bool = True,
    contrast: bool = True,
    denoise_strength: Optional[int] = 5,
    binarize_output: bool = False,
    max_width: int = 2000,
) -> np.ndarray:
    """Pipeline tiền xử lý ảnh hoàn chỉnh cho OCR."""
    _require_cv2()
    result = image
    result = resize_for_ocr(result, max_width=max_width)
    if grayscale:
        result = to_grayscale(result)
    if contrast:
        result = enhance_contrast(result)
    if denoise_strength:
        result = denoise(result, denoise_strength)
    if binarize_output:
        result = binarize(result)
    return result
