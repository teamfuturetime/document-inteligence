"""Browser-compatible previews without modifying stored originals."""

from io import BytesIO
from pathlib import Path

from document_images import open_image, rgb_page
from app.services.file_validation import image_limits


def image_preview(path: Path, page: int) -> tuple[bytes, int]:
    with open_image(path, path.suffix.lower().lstrip("."), **image_limits()) as (
        image,
        count,
    ):
        if page > count:
            raise IndexError("Trang xem trước không tồn tại")
        image.seek(page - 1)
        preview = rgb_page(image)
        # Only the display derivative is resized. OCR always uses the source.
        preview.thumbnail((2400, 2400))
        output = BytesIO()
        preview.save(output, format="PNG")
        return output.getvalue(), count
