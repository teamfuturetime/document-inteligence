"""Bounded image decoding shared by upload validation, preview and OCR."""

from contextlib import contextmanager
import warnings

from PIL import Image, ImageOps


IMAGE_FORMATS = {
    "png": ("PNG", {"image/png"}),
    "jpg": ("JPEG", {"image/jpeg"}),
    "jpeg": ("JPEG", {"image/jpeg"}),
    "webp": ("WEBP", {"image/webp"}),
    "bmp": ("BMP", {"image/bmp", "image/x-bmp", "image/x-ms-bmp"}),
    "tif": ("TIFF", {"image/tiff", "image/x-tiff"}),
    "tiff": ("TIFF", {"image/tiff", "image/x-tiff"}),
}
MIME_TYPES = {
    "pdf": {"application/pdf"},
    **{ext: value[1] for ext, value in IMAGE_FORMATS.items()},
}


def detect_extension(header: bytes) -> str | None:
    signatures = {
        "pdf": (b"%PDF",),
        "png": (b"\x89PNG\r\n\x1a\n",),
        "jpg": (b"\xff\xd8\xff",),
        "bmp": (b"BM",),
        "tif": (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"),
    }
    for extension, prefixes in signatures.items():
        if header.startswith(prefixes):
            return extension
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "webp"
    return None


def matching_extensions(left: str, right: str) -> bool:
    return (
        left == right
        or {left, right} <= {"jpg", "jpeg"}
        or {left, right} <= {"tif", "tiff"}
    )


@contextmanager
def open_image(
    source, extension: str, *, max_pixels: int, max_pages: int, max_total_pixels: int
):
    """Inspect dimensions before decoding; never retain a document's decoded pages."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            with Image.open(source, formats=[IMAGE_FORMATS[extension][0]]) as image:
                # Seek only up to the page limit; n_frames may scan an unbounded IFD chain.
                count = 0
                total_pixels = 0
                while True:
                    pixels = image.width * image.height
                    if pixels <= 0 or pixels > max_pixels:
                        raise ValueError("Ảnh vượt quá giới hạn số pixel")
                    total_pixels += pixels
                    if total_pixels > max_total_pixels:
                        raise ValueError(
                            "Tổng số pixel của tài liệu vượt quá giới hạn an toàn"
                        )
                    count += 1
                    if count > max_pages:
                        raise ValueError(f"Ảnh vượt quá giới hạn {max_pages} trang")
                    # Only TIFF is treated as a multipage document. Preserve first-frame
                    # behaviour for PNG/WebP animation without accepting GIF uploads.
                    if image.format != "TIFF":
                        break
                    try:
                        image.seek(count)
                    except EOFError:
                        break
                image.seek(0)
                yield image, count
        except (
            OSError,
            SyntaxError,
            EOFError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise ValueError(
                "Không thể giải mã ảnh hoặc ảnh vượt giới hạn an toàn"
            ) from exc


def validate_image(source, extension: str, **limits) -> None:
    # PNG verify checks data chunk CRCs that load alone may not inspect.
    with open_image(source, extension, **limits) as (image, _):
        image.verify()
    with open_image(source, extension, **limits) as (image, count):
        for index in range(count):
            image.seek(index)
            image.load()


def rgb_page(image: Image.Image) -> Image.Image:
    """Respect orientation and composite transparent pixels onto white for OCR."""
    image.load()
    oriented = ImageOps.exif_transpose(image)
    if oriented.mode.startswith("I;16"):
        # Converting 16-bit scans directly to RGB clips values above 255.
        # Scale the full sample range, retaining the previous 8-bit OCR input.
        oriented = oriented.convert("I").point(lambda value: value / 257).convert("L")
    if "A" in oriented.getbands() or "transparency" in oriented.info:
        rgba = oriented.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        return Image.alpha_composite(background, rgba).convert("RGB")
    return oriented.convert("RGB")
