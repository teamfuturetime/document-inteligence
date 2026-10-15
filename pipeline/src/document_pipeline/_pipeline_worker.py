"""Private worker; stdout is a JSON protocol, never engine stderr."""

import hashlib
import json
from pathlib import Path
import sys

from document_pipeline.extraction import RULES_SHA256, extract_invoice
from document_pipeline.ocr import recognize
from document_pipeline.preprocessing import MAX_FILE_BYTES, prepare_document


def main():
    try:
        data = sys.stdin.buffer.read(MAX_FILE_BYTES + 1)
        page = prepare_document(data)
        ocr = recognize(page, Path(sys.argv[1]))
        result = extract_invoice(ocr.result, sys.argv[2])
        config = {"preprocessing": page.metadata["config_sha256"],
                  "ocr": ocr.metadata["config_sha256"], "rules": RULES_SHA256}
        config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        result.pipeline_version = "invoice-pipeline-1.0.0"
        result.config_version = f"invoice-config-1.0.0:{config_hash[:12]}"
        print(json.dumps({"result": result.model_dump(), "ocr": ocr.result.model_dump(),
                          "metadata": {"ocr": ocr.metadata, "rules_sha256": RULES_SHA256,
                                       "config_sha256": config_hash, "config": config}}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": getattr(exc, "code", "internal_error")}))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
