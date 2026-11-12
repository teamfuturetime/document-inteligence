"""Explicit download of two small, pinned models; never runs during inference."""

import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path

from document_pipeline.tesseract import MODEL_LOCK


def main():
    parser = argparse.ArgumentParser(
        description="Fetch pinned vie+eng models into ignored runtime"
    )
    parser.add_argument(
        "--directory", type=Path, default=Path("runtime/models/tessdata_fast")
    )
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    for language, checksum in MODEL_LOCK["models"].items():
        target = args.directory / f"{language}.traineddata"
        if (
            target.is_file()
            and hashlib.sha256(target.read_bytes()).hexdigest() == checksum
        ):
            print(f"{language}: verified cached model")
            continue
        url = (
            "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/"
            f"{MODEL_LOCK['revision']}/{language}.traineddata"
        )
        temporary = None
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read(10 * 1024 * 1024 + 1)
            if (
                len(content) > 10 * 1024 * 1024
                or hashlib.sha256(content).hexdigest() != checksum
            ):
                raise ValueError(f"{language}: model checksum/size verification failed")
            with tempfile.NamedTemporaryFile(
                dir=args.directory, delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
            os.replace(temporary, target)
            print(f"{language}: downloaded and verified {len(content)} bytes")
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "revision": MODEL_LOCK["revision"],
                "languages": list(MODEL_LOCK["models"]),
            }
        )
    )


if __name__ == "__main__":
    main()
