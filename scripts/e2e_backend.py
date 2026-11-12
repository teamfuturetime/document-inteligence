"""Dedicated loopback native backend; isolated disposable runtime for browser tests."""

import tempfile
from pathlib import Path

import uvicorn
from docintel.api.app import create_app
from docintel.config import Settings


def main():
    with tempfile.TemporaryDirectory(prefix="docintel-browser-") as directory:
        settings = Settings(
            _env_file=None,
            provider_mode="tesseract",
            runtime_dir=Path(directory),
            cors_origins=["http://127.0.0.1:15173"],
        )
        uvicorn.run(
            create_app(settings), host="127.0.0.1", port=18811, log_level="warning"
        )


if __name__ == "__main__":
    main()
