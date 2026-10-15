"""Private subprocess entry point: one input document, one normalized page."""

from io import BytesIO
import json
import math
import sys

from PIL import Image, ImageOps, UnidentifiedImageError

from document_pipeline.preprocessing import MAX_FILE_BYTES, PreprocessingError


def orientation_transform(orientation: int, width: int, height: int) -> list[float]:
    # Coordinates describe continuous pixel edges (exclusive upper box bounds),
    # not pixel-center indexes. Map upright processed coordinates to raw source.
    transforms = {
        1: [1, 0, 0, 0, 1, 0],
        2: [-1, 0, width, 0, 1, 0],
        3: [-1, 0, width, 0, -1, height],
        4: [1, 0, 0, 0, -1, height],
        5: [0, 1, 0, 1, 0, 0],
        6: [0, 1, 0, -1, 0, height],
        7: [0, -1, width, -1, 0, height],
        8: [0, -1, width, 1, 0, 0],
    }
    return [float(value) for value in transforms.get(orientation, transforms[1]) + [0, 0, 1]]


def decode_image(data: bytes, max_pixels: int):
    try:
        with Image.open(BytesIO(data), formats=["PNG", "JPEG"]) as source:
            width, height = source.size
            if width * height > max_pixels:
                raise PreprocessingError("image_too_large", "Ảnh vượt giới hạn pixel.")
            media_type = "image/png" if source.format == "PNG" else "image/jpeg"
            source.verify()
        with Image.open(BytesIO(data), formats=["PNG", "JPEG"]) as source:
            if getattr(source, "n_frames", 1) != 1:
                raise PreprocessingError("multiple_pages", "Không hỗ trợ ảnh nhiều khung hình.")
            # PNG getexif() may load pixel data; verify the separate handle first.
            orientation = source.getexif().get(274, 1)
            upright = ImageOps.exif_transpose(source)
            rgba = upright.convert("RGBA")
            # Composite transparency onto white so transparent black is not OCR ink.
            white = Image.new("RGBA", rgba.size, "white")
            image = Image.alpha_composite(white, rgba).convert("L")
        return image, {
            "media_type": media_type, "source_width": width, "source_height": height,
            "source_coordinate_space": "raw_image_pixels",
            "to_original": orientation_transform(orientation, width, height),
        }
    except Image.DecompressionBombError as exc:
        raise PreprocessingError("image_too_large", "Ảnh vượt giới hạn decode.") from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise PreprocessingError("invalid_document", "Không đọc được ảnh.") from exc


def render_pdf(data: bytes, dpi: int, max_pixels: int):
    # PyMuPDF exists only in this disposable process, never in backend threads.
    import pymupdf

    try:
        with pymupdf.open(stream=data, filetype="pdf") as document:
            if document.needs_pass or document.is_repaired:
                raise PreprocessingError("invalid_document", "PDF có mật khẩu hoặc cấu trúc lỗi.")
            if document.page_count != 1:
                raise PreprocessingError("multiple_pages", "MVP chỉ hỗ trợ PDF một trang.")
            page = document[0]
            width, height = page.rect.width, page.rect.height
            if not all(math.isfinite(value) and value > 0 for value in (width, height)):
                raise PreprocessingError("invalid_document", "Kích thước trang PDF không hợp lệ.")
            if math.ceil(width * dpi / 72) * math.ceil(height * dpi / 72) > max_pixels:
                raise PreprocessingError("image_too_large", "Trang PDF vượt giới hạn raster pixel.")
            pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples).convert("L")
            if image.width * image.height > max_pixels:
                raise PreprocessingError("image_too_large", "Trang PDF vượt giới hạn raster pixel.")
            return image, {
                "media_type": "application/pdf", "pdf_dpi": dpi,
                "pdf_page_width_points": width, "pdf_page_height_points": height,
                "source_width": image.width, "source_height": image.height,
                "source_coordinate_space": "pdf_raster_pixels",
                "to_original": orientation_transform(1, image.width, image.height),
            }
    except PreprocessingError:
        raise
    except (RuntimeError, ValueError) as exc:
        raise PreprocessingError("invalid_document", "Không render được PDF.") from exc


def main():
    try:
        dpi, max_pixels = map(int, sys.argv[1:])
        data = sys.stdin.buffer.read(MAX_FILE_BYTES + 1)
        if not data or len(data) > MAX_FILE_BYTES:
            raise PreprocessingError("invalid_document", "Input worker không hợp lệ.")
        if data.startswith(b"%PDF-"):
            image, metadata = render_pdf(data, dpi, max_pixels)
        elif data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8"):
            image, metadata = decode_image(data, max_pixels)
        else:
            raise PreprocessingError("unsupported_media_type", "Chỉ hỗ trợ nội dung PNG, JPEG, PDF.")
        metadata.update(width=image.width, height=image.height, page=1, color_mode="L")
        output = BytesIO()
        image.save(output, format="PNG")
        sys.stdout.buffer.write(json.dumps(metadata).encode() + b"\n" + output.getvalue())
    except Exception as exc:
        code = exc.code if isinstance(exc, PreprocessingError) else "internal_error"
        message = str(exc) if isinstance(exc, PreprocessingError) else "Preprocessing worker thất bại."
        sys.stdout.buffer.write(json.dumps({"error": {"code": code, "message": message}}).encode() + b"\n")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
