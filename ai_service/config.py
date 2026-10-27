"""Cấu hình nhỏ, độc lập với backend và database."""
import os

OCR_ENGINE = os.getenv("OCR_ENGINE", "tesseract").lower()
OCR_LANG = os.getenv("OCR_LANG", "vie")
OCR_FALLBACK_ENABLED = os.getenv("OCR_FALLBACK_ENABLED", "false").lower() in {"1", "true", "yes"}
OCR_PSM_MODES = tuple(
    int(value.strip())
    for value in os.getenv("OCR_PSM_MODES", "3,4,6,11").split(",")
    if value.strip().isdigit()
) or (3,)
OCR_MAX_ATTEMPTS = max(1, min(int(os.getenv("OCR_MAX_ATTEMPTS", "3")), 4))
PDF_DPI = max(150, min(int(os.getenv("PDF_DPI", "250")), 300))
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "20"))
MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "40000000"))
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
REVIEW_THRESHOLD = float(os.getenv("CLASSIFICATION_REVIEW_THRESHOLD", "70"))
