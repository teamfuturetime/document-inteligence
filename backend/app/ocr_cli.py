"""Local OCR smoke runner: python -m app.ocr_cli IMAGE [--tessdata-dir PATH]."""

import argparse
from pathlib import Path
import sys

from app.providers.contracts import ProviderError
from app.providers.tesseract import TesseractOCRProvider
from app.schemas.extraction import DocumentInput


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR only; does not extract invoice fields")
    parser.add_argument("image", type=Path)
    parser.add_argument("--tesseract", default="tesseract")
    parser.add_argument("--tessdata-dir", type=Path)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(args.image.suffix.lower())
    if media is None:
        parser.error("Expected PNG or JPEG")
    try:
        document = DocumentInput(document_id=args.image.stem, media_type=media, content=args.image.read_bytes())
        result = TesseractOCRProvider(args.tesseract, tessdata_dir=args.tessdata_dir,
                                      timeout_seconds=args.timeout).recognize(document)
    except ProviderError as exc:
        print(exc.code, file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print("invalid_input", file=sys.stderr)
        return 1
    # Explicit CLI output only; the adapter itself never logs document content.
    sys.stdout.buffer.write((result.model_dump_json(indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
