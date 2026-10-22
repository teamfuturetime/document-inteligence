"""Cấu hình nhỏ, độc lập với backend và database."""
import os

OCR_ENGINE = os.getenv("OCR_ENGINE", "tesseract").lower()
OCR_LANG = os.getenv("OCR_LANG", "vie")
OCR_FALLBACK_ENABLED = os.getenv("OCR_FALLBACK_ENABLED", "false").lower() in {"1", "true", "yes"}
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
REVIEW_THRESHOLD = float(os.getenv("CLASSIFICATION_REVIEW_THRESHOLD", "70"))
