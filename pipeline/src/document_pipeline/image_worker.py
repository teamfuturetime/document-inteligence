"""Private IPC entry point. Never imports web, storage, evaluation or labels."""

import io
import json
import sys
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from document_pipeline.config import PipelineConfig
from document_pipeline.errors import PipelineError


def decode_image(data: bytes, max_pixels: int) -> Image.Image:
    with Image.open(io.BytesIO(data)) as source:
        if source.format not in ("PNG", "JPEG") or getattr(source, "n_frames", 1) != 1:
            raise PipelineError(
                "UNSUPPORTED_MEDIA_TYPE", "Chỉ hỗ trợ PNG, JPEG hoặc PDF một trang."
            )
        if source.width * source.height > max_pixels:
            raise PipelineError("IMAGE_TOO_LARGE", "Ảnh vượt giới hạn pixel.")
        image = ImageOps.exif_transpose(source).convert("RGBA")
        background = Image.new("RGBA", image.size, "white")
        return Image.alpha_composite(background, image).convert("RGB")


def main() -> int:
    config = PipelineConfig.model_validate_json(sys.argv[1])
    data = sys.stdin.buffer.read(config.max_upload_bytes + 1)
    if len(data) > config.max_upload_bytes:
        print(json.dumps({"error": "FILE_TOO_LARGE"}))
        return 1

    try:
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        is_pdf = data.startswith(b"%PDF-")
        if is_pdf:
            from document_pipeline.pdf import check_raster_size, render_single_page

            image, metadata = render_single_page(data, config.max_image_pixels)
        else:
            image = decode_image(data, config.max_image_pixels)
            metadata = {
                "version": "image-preprocessing-1.0.0",
                "source_frame": "exif_normalized_pixels_top_left",
            }

        width, height = image.size
        if config.rotation:
            image = image.rotate(-config.rotation, expand=True)
        target = (
            max(1, round(image.width * config.scale)),
            max(1, round(image.height * config.scale)),
        )
        if is_pdf:
            check_raster_size(*target, config.max_image_pixels)
        elif target[0] * target[1] > config.max_image_pixels:
            raise PipelineError("IMAGE_TOO_LARGE", "Ảnh vượt giới hạn pixel.")
        image = image.convert("L")
        if image.size != target:
            image = image.resize(target, Image.Resampling.LANCZOS)
        if config.autocontrast:
            image = ImageOps.autocontrast(image)
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        metadata.update(
            width=width,
            height=height,
            processed_width=image.width,
            processed_height=image.height,
            rotation=config.rotation,
            scale=config.scale,
        )
        sys.stdout.buffer.write(json.dumps(metadata).encode() + b"\n" + stream.getvalue())
        return 0
    except PipelineError as exc:
        print(json.dumps({"error": exc.code}))
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        print(json.dumps({"error": "IMAGE_TOO_LARGE"}))
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        print(json.dumps({"error": "INVALID_PDF" if is_pdf else "INVALID_DOCUMENT"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
