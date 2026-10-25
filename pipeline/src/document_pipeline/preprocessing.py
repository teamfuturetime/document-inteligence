"""Image decoding is isolated so corrupt/native decoders have a deadline."""

import json
import subprocess
import sys
from dataclasses import dataclass

from document_pipeline.config import PipelineConfig
from document_pipeline.errors import PipelineError


@dataclass(frozen=True)
class PreparedImage:
    png: bytes
    width: int
    height: int
    processed_width: int
    processed_height: int
    metadata: dict

    def source_box(self, box: tuple[int, int, int, int]) -> tuple[float, float, float, float]:
        """Project a processed rectangle onto the EXIF-normalized source image."""
        rotation = self.metadata["rotation"]
        width, height = self.width, self.height
        rotated_w, rotated_h = (height, width) if rotation in (90, 270) else (width, height)
        points = []
        for x, y in ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])):
            x, y = x * rotated_w / self.processed_width, y * rotated_h / self.processed_height
            if rotation == 90:
                x, y = y, height - x
            elif rotation == 180:
                x, y = width - x, height - y
            elif rotation == 270:
                x, y = width - y, x
            points.append((max(0.0, min(width, x)), max(0.0, min(height, y))))
        return (
            min(p[0] for p in points),
            min(p[1] for p in points),
            max(p[0] for p in points),
            max(p[1] for p in points),
        )


def prepare_image(data: bytes, config: PipelineConfig) -> PreparedImage:
    if not data:
        raise PipelineError("INVALID_DOCUMENT", "Tài liệu rỗng.")
    if len(data) > config.max_upload_bytes:
        raise PipelineError("FILE_TOO_LARGE", "Tài liệu vượt giới hạn kích thước.")
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "document_pipeline.image_worker", config.model_dump_json()],
            input=data,
            capture_output=True,
            timeout=config.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PipelineError("PROCESSING_TIMEOUT", "Tiền xử lý quá thời gian.") from exc
    except OSError as exc:
        raise PipelineError("PROVIDER_UNAVAILABLE", "Không khởi động được xử lý ảnh.") from exc
    try:
        header, separator, png = completed.stdout.partition(b"\n")
        metadata = json.loads(header)
        if completed.returncode:
            code = metadata.get("error", "INVALID_DOCUMENT")
            if code not in {"INVALID_DOCUMENT", "IMAGE_TOO_LARGE", "UNSUPPORTED_MEDIA_TYPE"}:
                code = "INVALID_DOCUMENT"
            raise PipelineError(code, "Ảnh không hợp lệ hoặc không được hỗ trợ.")
        if not separator or not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("invalid worker response")
        return PreparedImage(
            png=png,
            width=metadata["width"],
            height=metadata["height"],
            processed_width=metadata["processed_width"],
            processed_height=metadata["processed_height"],
            metadata=metadata,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise PipelineError("INVALID_DOCUMENT", "Không đọc được ảnh đã tiền xử lý.") from exc
