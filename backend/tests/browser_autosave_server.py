"""Explicit synthetic OCR double for real HTTP/browser review tests, never native evidence."""

import sys
import tempfile
from pathlib import Path

import uvicorn
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
from test_product import processed  # noqa: E402

from docintel.api.app import create_app  # noqa: E402
from docintel.config import Settings  # noqa: E402
from docintel.services.documents import DocumentService  # noqa: E402

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="autosave-browser-") as directory:
        DocumentService.ensure_ready = lambda self: {}
        app = create_app(
            Settings(
                _env_file=None,
                provider_mode="tesseract",
                runtime_dir=Path(directory),
                cors_origins=["http://127.0.0.1:15174"],
            ),
            start_worker=False,
        )
        with TestClient(app) as api:
            from test_product import inference

            api.app.state.documents.pipeline.run = inference
            for _ in range(10):
                processed(api)
            uvicorn.run(app, host="127.0.0.1", port=18812, log_level="warning")
