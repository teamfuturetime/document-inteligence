from pathlib import Path

import cv2
import fitz
import numpy as np

from ai_service.preprocessing.image import decode_image


def pdf_to_images(content: bytes, dpi: int = 200) -> list[np.ndarray]:
    document = fitz.open(stream=content, filetype="pdf")
    if document.page_count == 0:
        raise ValueError("PDF has no pages")
    scale = dpi / 72
    pages: list[np.ndarray] = []
    for page in document:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        array = np.frombuffer(pixmap.samples, dtype=np.uint8)
        pages.append(array.reshape(pixmap.height, pixmap.width, pixmap.n))
    return pages


def deskew(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    points = np.column_stack(np.where(gray < 200))
    if len(points) < 20:
        return image.copy()
    angle = cv2.minAreaRect(points[:, ::-1].astype(np.float32))[-1]
    if angle > 45:
        angle -= 90
    elif angle < -45:
        angle += 90
    if abs(angle) > 15:
        return image.copy()
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderValue=255)


def load_pages(content: bytes, filename: str) -> list[np.ndarray]:
    if Path(filename).suffix.lower() == ".pdf":
        return pdf_to_images(content)
    return [decode_image(content)]
