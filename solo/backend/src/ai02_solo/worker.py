"""Private worker protocol: bytes in, safe JSON out; never log document content."""

import json
import sys

from .ocr import DocumentError, MAX_BYTES
from .pipeline import run_inline
from .settings import Settings


def main():
    try:
        result = run_inline(sys.stdin.buffer.read(MAX_BYTES + 1), sys.argv[1], sys.argv[2],
                            Settings(**json.loads(sys.argv[3])))
        print(result.model_dump_json())
    except DocumentError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message, "status": exc.status}}))
    except Exception:
        print(json.dumps({"error": {"code": "processing_failed", "message": "Không xử lý được tài liệu.", "status": 500}}))


if __name__ == "__main__":
    main()
