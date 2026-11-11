"""One pipeline for API and evaluation, with a disposable process group."""

from dataclasses import asdict
import hashlib
import json
import os
import signal
import subprocess
import sys

from .contracts import Extraction, LABELS
from .extract import align_vlm, fuse, lines, rule_extract, text
from .ocr import DocumentError, MAX_BYTES, prepare, recognize
from .settings import Settings
from .vlm import extract_vlm


def run_inline(data, kind, mode, settings):
    png = prepare(data)
    tokens, ocr_metadata = recognize(png, settings.tessdata_dir)
    ocr_text = "\n".join(text(group) for group in lines(tokens))
    baseline = rule_extract(kind, tokens)
    provenance = {"pipeline_version": "solo-1.0", "rules_version": "solo-labels-1",
        "rules_sha256": hashlib.sha256(json.dumps(LABELS, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "ocr": ocr_metadata}
    fields = baseline
    if mode != "rules":
        values, vlm_metadata = extract_vlm(png, ocr_text, kind, settings)
        vision = align_vlm(kind, values, tokens)
        fields = fuse(baseline, vision) if mode == "hybrid" else vision
        provenance["vlm"] = vlm_metadata
    return Extraction(document_type=kind, document_sha256=hashlib.sha256(data).hexdigest(), mode=mode,
        fields=fields, ocr_text=ocr_text, provenance=provenance,
        warnings=[] if tokens else ["OCR không nhận diện được chữ. Kiểm tra độ rõ và chiều tài liệu."])


def run(data: bytes, kind, mode, settings: Settings):
    if not data or len(data) > MAX_BYTES:
        raise DocumentError("file_size", "Tài liệu trống hoặc lớn hơn 10 MiB.", 413)
    if os.name != "posix":
        raise DocumentError("platform", "Bản local hiện hỗ trợ macOS/Linux.", 503)
    process = subprocess.Popen([sys.executable, "-m", "ai02_solo.worker", kind, mode, json.dumps(asdict(settings))],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        output, _ = process.communicate(data, timeout=settings.deadline)
        if process.returncode:
            raise DocumentError("processing_failed", "Pipeline không xử lý được tài liệu.")
        payload = json.loads(output)
        if "error" in payload:
            error = payload["error"]
            raise DocumentError(error["code"], error["message"], error["status"])
        return Extraction.model_validate_json(output)
    except subprocess.TimeoutExpired as exc:
        raise DocumentError("timeout", "Hết thời gian xử lý; thử ảnh nhỏ hơn hoặc kiểm tra server VLM.", 504) from exc
    except (ValueError, KeyError) as exc:
        raise DocumentError("processing_failed", "Pipeline trả dữ liệu không hợp lệ.", 500) from exc
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()


def source_hash():
    from pathlib import Path
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
