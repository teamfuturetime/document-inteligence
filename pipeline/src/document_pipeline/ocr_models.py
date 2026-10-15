"""Explicit model installation; recognition never downloads or changes models."""

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.error import URLError
from urllib.request import urlopen

MODEL_LOCK = json.loads(Path(__file__).with_name("tessdata-lock.json").read_text())
MAX_MODEL_BYTES = 20 * 1024 * 1024
MODELSET_SHA256 = hashlib.sha256(
    json.dumps(MODEL_LOCK, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()


class ModelError(Exception):
    code = "ocr_unavailable"


def verify_model(path: Path, expected: str) -> None:
    try:
        if path.stat().st_size > MAX_MODEL_BYTES:
            raise ModelError("Model OCR vượt giới hạn dung lượng.")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(64 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ModelError("Hash model OCR không khớp tessdata-lock.json.")
    except OSError as exc:
        raise ModelError("Thiếu hoặc không đọc được model OCR đã pin.") from exc


def verify_models(directory: Path) -> dict[str, str]:
    for language, expected in MODEL_LOCK["models"].items():
        verify_model(directory / f"{language}.traineddata", expected)
    return dict(MODEL_LOCK["models"])


def install_models(directory: Path) -> None:
    """Download pinned official files, verify before atomic replacement, clean up."""
    directory.mkdir(parents=True, exist_ok=True)
    for language, expected in MODEL_LOCK["models"].items():
        destination = directory / f"{language}.traineddata"
        try:
            verify_model(destination, expected)
            continue
        except ModelError:
            pass
        url = ("https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/"
               f"{MODEL_LOCK['revision']}/{language}.traineddata")
        temporary = None
        try:
            with urlopen(url, timeout=30) as response, tempfile.NamedTemporaryFile(
                dir=directory, prefix=f".{language}-", suffix=".download", delete=False,
            ) as stream:
                temporary = Path(stream.name)
                total = 0
                while chunk := response.read(64 * 1024):
                    total += len(chunk)
                    if total > MAX_MODEL_BYTES:
                        raise ModelError("Model tải về vượt giới hạn dung lượng.")
                    stream.write(chunk)
            verify_model(temporary, expected)
            temporary.replace(destination)
        except (OSError, URLError) as exc:
            raise ModelError("Không tải được model OCR từ nguồn đã pin.") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Install pinned official vie/eng OCR models.")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--check", action="store_true", help="Verify only; no network or writes")
    args = parser.parse_args()
    try:
        if not args.check:
            install_models(args.directory)
        print(json.dumps({"revision": MODEL_LOCK["revision"],
                          "models": verify_models(args.directory)}, indent=2))
    except (ModelError, OSError) as exc:
        parser.exit(1, f"ocr_unavailable: {exc}\n")


if __name__ == "__main__":
    main()
