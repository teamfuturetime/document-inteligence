"""Select OCR without silently falling back between local and external services."""

from . import ocr, ocrspace


def available(settings):
    return {"tesseract": ocr.readiness(settings.tessdata_dir), "ocrspace": ocrspace.readiness(settings)}


def recognize(png, settings):
    if settings.ocr_provider == "tesseract":
        tokens, metadata = ocr.recognize(png, settings.tessdata_dir)
        return tokens, {**metadata, "provider": "tesseract", "confidence_available": True}
    if settings.ocr_provider == "ocrspace":
        return ocrspace.recognize(png, settings)
    raise ocr.DocumentError("ocr_provider", "Nguồn OCR không được hỗ trợ.", 503)
