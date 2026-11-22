"""Render one bounded PDF page inside the disposable preprocessing subprocess."""

import math
from contextlib import closing

import pypdfium2 as pdfium
from pypdfium2 import raw

from document_pipeline.errors import PipelineError

PDF_DPI = 200
MAX_PDF_RASTER_SIDE = 8192
PDF_PREPROCESSING_VERSION = "pdfium-raster-1.0.0"


def check_raster_size(width: int, height: int, max_pixels: int) -> None:
    if max(width, height) > MAX_PDF_RASTER_SIDE or width * height > max_pixels:
        raise PipelineError("IMAGE_TOO_LARGE", "Trang PDF vượt giới hạn raster.")


def render_single_page(data: bytes, max_pixels: int):
    if not data.rstrip(b"\x00\t\n\f\r ").endswith(b"%%EOF"):
        raise PipelineError("INVALID_PDF", "PDF không có marker kết thúc hợp lệ.")

    scale = PDF_DPI / 72
    try:
        with pdfium.PdfDocument(data) as document:
            # An encrypted document can sometimes open with an empty user password.
            if raw.FPDF_GetSecurityHandlerRevision(document) >= 0:
                raise PipelineError("PDF_ENCRYPTED", "PDF có mã hóa.")
            if len(document) != 1:
                raise PipelineError("PDF_PAGE_COUNT", "Chỉ hỗ trợ PDF đúng một trang.")
            with closing(document[0]) as page:
                width, height = page.get_size()
                if not all(math.isfinite(side) and side > 0 for side in (width, height)):
                    raise PipelineError("INVALID_PDF", "Kích thước trang không hợp lệ.")
                check_raster_size(math.ceil(width * scale), math.ceil(height * scale), max_pixels)
                with closing(
                    page.render(
                        scale=scale,
                        grayscale=True,
                        draw_annots=False,
                        may_draw_forms=False,
                        limit_image_cache=True,
                    )
                ) as bitmap:
                    check_raster_size(bitmap.width, bitmap.height, max_pixels)
                    # Copy before closing the native bitmap backing the Pillow image.
                    image = bitmap.to_pil().copy()
    except pdfium.PdfiumError as exc:
        if exc.err_code in (raw.FPDF_ERR_PASSWORD, raw.FPDF_ERR_SECURITY):
            raise PipelineError("PDF_ENCRYPTED", "PDF có mã hóa.") from exc
        raise PipelineError("INVALID_PDF", "Không đọc được PDF.") from exc

    return image, {
        "version": PDF_PREPROCESSING_VERSION,
        "source_frame": "pdf_raster_pixels_top_left",
        "media_type": "application/pdf",
        "pdf_dpi": PDF_DPI,
        "pdfium_version": str(pdfium.PDFIUM_INFO.version),
        "pypdfium2_version": str(pdfium.PYPDFIUM_INFO.version),
        "page_index": 0,
    }
