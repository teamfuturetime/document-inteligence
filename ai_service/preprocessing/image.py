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


def resize_to_max_width(image: np.ndarray, max_width: int = 2000) -> np.ndarray:
    """Thu nhỏ ảnh nếu vượt quá chiều rộng tối đa (giảm RAM)."""
    _require_cv2()
    h, w = image.shape[:2]
    if w <= max_width:
        return image
    scale = max_width / w
    new_size = (max_width, int(h * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def preprocess_image(
    image: np.ndarray,
    *,
    grayscale: bool = True,
    contrast: bool = True,
    denoise_strength: Optional[int] = 10,
    binarize_output: bool = False,
    max_width: int = 2000,
) -> np.ndarray:
    """Pipeline tiền xử lý ảnh hoàn chỉnh cho OCR."""
    _require_cv2()
    result = image
    result = resize_to_max_width(result, max_width)
    if grayscale:
        result = to_grayscale(result)
    if contrast:
        result = enhance_contrast(result)
    if denoise_strength:
        result = denoise(result, denoise_strength)
    if binarize_output:
        result = binarize(result)
    return result
