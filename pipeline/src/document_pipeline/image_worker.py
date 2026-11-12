"""Private IPC entry point. Never imports web, storage, evaluation or labels."""

import io
import json
import sys
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from document_pipeline.config import PipelineConfig


def main() -> int:
    config = PipelineConfig.model_validate_json(sys.argv[1])
    data = sys.stdin.buffer.read(config.max_upload_bytes + 1)
    try:
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in ("PNG", "JPEG") or getattr(source, "n_frames", 1) != 1:
                print(json.dumps({"error": "UNSUPPORTED_MEDIA_TYPE"}))
                return 1
            if source.width * source.height > config.max_image_pixels:
                print(json.dumps({"error": "IMAGE_TOO_LARGE"}))
                return 1
            image = ImageOps.exif_transpose(source).convert("RGBA")
            background = Image.new("RGBA", image.size, "white")
            image = Image.alpha_composite(background, image).convert("RGB")
            width, height = image.size
            # Preview is generated with identity config; OCR can use explicit rotation/scale.
            if config.rotation:
                image = image.rotate(-config.rotation, expand=True)
            target = (
                max(1, round(image.width * config.scale)),
                max(1, round(image.height * config.scale)),
            )
            if target[0] * target[1] > config.max_image_pixels:
                print(json.dumps({"error": "IMAGE_TOO_LARGE"}))
                return 1
            image = image.convert("L")
            if image.size != target:
                image = image.resize(target, Image.Resampling.LANCZOS)
            if config.autocontrast:
                image = ImageOps.autocontrast(image)
            stream = io.BytesIO()
            image.save(stream, format="PNG")
            metadata = {
                "version": "image-preprocessing-1.0.0",
                "width": width,
                "height": height,
                "processed_width": image.width,
                "processed_height": image.height,
                "rotation": config.rotation,
                "scale": config.scale,
                "source_frame": "exif_normalized_pixels_top_left",
            }
            sys.stdout.buffer.write(json.dumps(metadata).encode() + b"\n" + stream.getvalue())
            return 0
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        print(json.dumps({"error": "IMAGE_TOO_LARGE"}))
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        print(json.dumps({"error": "INVALID_DOCUMENT"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
