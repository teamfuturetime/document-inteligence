"""OCR.space POST adapter; no credentials in Settings, argv, responses or reports."""

import hashlib
import json
import math
import os
from pathlib import Path
import urllib.error
import urllib.request
import uuid

from .contracts import Token
from .ocr import DocumentError

ENDPOINT = "https://api.ocr.space/parse/image"
MAX_FILE_BYTES = 1_000_000  # Conservative free-tier 1 MB ceiling, after preprocessing.
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


def api_key(settings):
    value = os.getenv("SOLO_OCRSPACE_API_KEY")
    if value is None:
        try:
            path = Path(settings.ocrspace_key_file)
            if path.stat().st_size > 4096:
                return ""
            value = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return ""
    value = value.strip()
    return value if 0 < len(value) <= 4096 and "\r" not in value and "\n" not in value else ""


def readiness(settings):
    configured = bool(api_key(settings))
    return {"ready": configured, "configured": configured, "configuration_only": True,
            "reason": None if configured else "Cần cấu hình API key OCR.space ở backend.",
            "engine": f"OCR.space Engine {settings.ocrspace_engine}", "confidence_available": False}


def parameters(settings):
    if settings.ocrspace_engine not in {2, 3}:
        raise DocumentError("ocrspace_config", "OCR.space chỉ cho phép Engine 2 hoặc 3.", 503)
    return {"OCREngine": str(settings.ocrspace_engine), "language": "auto", "isOverlayRequired": "true",
            "isTable": "true", "scale": "false", "detectOrientation": "false", "isCreateSearchablePdf": "false"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post_image(png, key, params):
    boundary = "ai02-" + uuid.uuid4().hex
    parts = []
    for name, value in params.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="document.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + png + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    request = urllib.request.Request(ENDPOINT, data=b"".join(parts),
        headers={"apikey": key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=60) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("response limit")
        return json.loads(data)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise DocumentError("ocrspace_quota", "OCR.space đã giới hạn lượt gọi; thử lại sau hoặc chọn Tesseract local.", 429) from None
        if exc.code in {401, 403}:
            raise DocumentError("ocrspace_auth", "OCR.space từ chối API key; kiểm tra cấu hình backend.", 503) from None
        raise DocumentError("ocrspace_unavailable", "Không gọi được dịch vụ OCR.space.", 503) from None
    except (TimeoutError, urllib.error.URLError, OSError):
        raise DocumentError("ocrspace_unavailable", "OCR.space chưa phản hồi hoặc kết nối bị lỗi; không tự chuyển engine.", 503) from None
    except ValueError:
        raise DocumentError("ocrspace_output", "OCR.space trả response quá lớn hoặc JSON không hợp lệ.", 502) from None


def parse_response(payload):
    try:
        if not isinstance(payload, dict):
            raise ValueError("object required")
        if payload.get("IsErroredOnProcessing") is not False or str(payload.get("OCRExitCode")) != "1":
            # Classify errors, but never reflect provider text that could echo a credential.
            message = str(payload.get("ErrorMessage", "")).lower()
            if any(word in message for word in ["api key", "apikey", "invalid key"]):
                raise DocumentError("ocrspace_auth", "OCR.space từ chối API key; kiểm tra cấu hình backend.", 503)
            if any(word in message for word in ["quota", "rate limit", "maximum number", "requests per"]):
                raise DocumentError("ocrspace_quota", "OCR.space đã hết quota hoặc giới hạn lượt gọi.", 429)
            raise DocumentError("ocrspace_processing", "OCR.space không xử lý thành công toàn bộ tài liệu.", 502)
        pages = payload["ParsedResults"]
        if not isinstance(pages, list) or len(pages) != 1:
            raise ValueError("exactly one page required")
        page = pages[0]
        if str(page.get("FileParseExitCode")) != "1":
            raise ValueError("page failed")
        parsed_text = page["ParsedText"]
        if not isinstance(parsed_text, str):
            raise ValueError("text required")
        overlay = page.get("TextOverlay") or {}
        lines = overlay.get("Lines", [])
        if not isinstance(lines, list) or len(lines) > 5000:
            raise ValueError("invalid overlay")
        tokens = []
        for index, line in enumerate(lines):
            for word in line["Words"]:
                raw = word["WordText"]
                if not isinstance(raw, str) or not raw.strip() or len(raw) > 2000:
                    raise ValueError("invalid word")
                numbers = [word[k] for k in ["Left", "Top", "Width", "Height"]]
                if any(type(value) not in {int, float} or not math.isfinite(value) for value in numbers):
                    raise ValueError("invalid geometry")
                left, top, width, height = numbers
                if min(left, top) < 0 or min(width, height) <= 0 or max(left + width, top + height) > 100_000:
                    raise ValueError("invalid geometry")
                tokens.append(Token(text=raw, confidence=None,
                    box=(math.floor(left), math.floor(top), math.ceil(left + width), math.ceil(top + height)),
                    line=(1, 1, index + 1)))
                if len(tokens) > 20_000:
                    raise ValueError("token limit")
        if parsed_text.strip() and (overlay.get("HasOverlay") is not True or not tokens):
            raise ValueError("missing overlay; cannot invent evidence")
        return tokens
    except (ValueError, KeyError, TypeError, AttributeError):
        raise DocumentError("ocrspace_output", "OCR.space trả kết quả/overlay không hợp lệ hoặc thiếu trang.", 502) from None


def recognize(png, settings):
    key = api_key(settings)
    if not key:
        raise DocumentError("ocrspace_not_configured", "Chưa cấu hình API key OCR.space ở backend.", 503)
    if len(png) > MAX_FILE_BYTES:
        raise DocumentError("ocrspace_file_size", "Ảnh sau tiền xử lý vượt 1 MB của OCR.space Free; dùng ảnh nhỏ hơn hoặc Tesseract local.", 413)
    params = parameters(settings)
    tokens = parse_response(post_image(png, key, params))
    return tokens, {"provider": "ocrspace", "engine": f"OCR.space Engine {settings.ocrspace_engine}",
        "adapter_version": "ocrspace-1", "language": "auto", "confidence_available": False,
        "model_revision": None, "version_source": "service_managed_unpinned",
        "parameters": params, "config_sha256": hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest(),
        "preprocessing": "gray-exif-pdf150-v1"}
