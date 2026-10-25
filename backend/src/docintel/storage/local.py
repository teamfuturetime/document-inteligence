import os
from pathlib import Path


class LocalDocumentStorage:
    """Only server-generated hex document IDs become file names."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, document_id: str, kind: str) -> Path:
        if len(document_id) != 32 or any(char not in "0123456789abcdef" for char in document_id):
            raise ValueError("Invalid storage identifier")
        if kind not in ("source", "preview"):
            raise ValueError("Invalid storage kind")
        return self.root / f"{document_id}.{kind}"

    def write(self, document_id: str, kind: str, data: bytes):
        target = self.path(document_id, kind)
        with target.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

    def discard(self, document_id: str):
        for kind in ("source", "preview"):
            self.path(document_id, kind).unlink(missing_ok=True)
