"""Chuyển PDF thành ảnh (PyMuPDF) và hiệu chỉnh nghiêng (OpenCV)."""
from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np

try:
    import cv2

    _HAS_CV2 = True
except ImportError:  # pragma: no cover
    _HAS_CV2 = False

try:
    import fitz  # PyMuPDF

    _HAS_FITZ = True
except ImportError:  # pragma: no cover
    _HAS_FITZ = False

from ai_service.preprocessing.image import PreprocessingError, to_grayscale
from ai_service.config import MAX_IMAGE_PIXELS, MAX_PDF_PAGES


def pdf_to_images(pdf_path: str, dpi: int = 200) -> List[np.ndarray]:
    """Chuyển từng trang PDF thành ảnh numpy array."""
    if not _HAS_FITZ:
        raise PreprocessingError(
            "PyMuPDF chưa được cài đặt. Chạy: pip install PyMuPDF"
        )
    path = Path(pdf_path)
    if not path.exists():
        raise PreprocessingError(f"File PDF không tồn tại: {pdf_path}")

    images: List[np.ndarray] = []
    with fitz.open(path) as doc:
        if doc.page_count == 0:
            raise PreprocessingError("PDF không có trang")
        if doc.page_count > MAX_PDF_PAGES:
            raise PreprocessingError(f"PDF vượt quá giới hạn {MAX_PDF_PAGES} trang")
        for page in doc:
            # Render trang ở DPI mong muốn
            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            if pix.width * pix.height > MAX_IMAGE_PIXELS:
                raise PreprocessingError("Trang PDF vượt quá giới hạn kích thước ảnh")
            # Chuyển sang numpy array (RGB)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            if pix.n == 4:  # RGBA -> BGR
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:  # RGB -> BGR
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            images.append(img)
    return images


def estimate_skew_angle(image: np.ndarray) -> float:
    """Ước lượng góc nghiêng của ảnh bằng Hough transform."""
    _require_cv2()
    gray = to_grayscale(image)
    # Nhị phân hóa và phát hiện cạnh
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    edges = cv2.Canny(binary, 50, 150, apertureSize=3)

    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10
    )
    if lines is None or len(lines) == 0:
        return 0.0

    angles = []
    for line in lines:
        # OpenCV < 4.5 trả về shape (N, 1, 4); OpenCV >= 4.5 trả về (N, 4)
        if line.ndim == 2 and line.shape[1] == 4:
            x1, y1, x2, y2 = line[0]
        else:
            x1, y1, x2, y2 = line
        if abs(x2 - x1) < 1e-6:
            continue
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Chỉ xét các đường gần ngang (tránh đường dọc)
        if abs(angle) < 45:
            angles.append(angle)

    if not angles:
        return 0.0
    # Góc nghiêng = median của các góc đường kẻ
    return float(np.median(angles))


def deskew(image: np.ndarray, max_angle: float = 10.0) -> np.ndarray:
    """Xoay ảnh để hiệu chỉnh nghiêng, giới hạn góc tối đa."""
    _require_cv2()
    angle = estimate_skew_angle(image)
    if abs(angle) < 0.5 or abs(angle) > max_angle:
        # Góc quá nhỏ (không cần xoay) hoặc quá lớn (nghi ngờ sai)
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def preprocess_document(
    pdf_path: str,
    *,
    dpi: int = 200,
    deskew_enabled: bool = True,
    max_angle: float = 10.0,
) -> List[np.ndarray]:
    """Pipeline chuyển PDF → ảnh → deskew cho từng trang."""
    images = pdf_to_images(pdf_path, dpi=dpi)
    if deskew_enabled:
        images = [deskew(img, max_angle=max_angle) for img in images]
    return images


def _require_cv2() -> None:
    if not _HAS_CV2:
        raise PreprocessingError(
            "OpenCV chưa được cài đặt. Chạy: pip install opencv-python-headless"
        )
