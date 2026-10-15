import os
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredFile:
    original_name: str
    stored_name: str
    path: Path
    size_bytes: int


class LocalStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, original_name: str, content: bytes) -> StoredFile:
        suffix = Path(original_name).suffix.lower()
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        destination = self.root / stored_name
        temp_path = self.root / f".{stored_name}.tmp"
        temp_path.write_bytes(content)
        os.replace(temp_path, destination)
        return StoredFile(
            original_name=Path(original_name).name,
            stored_name=stored_name,
            path=destination,
            size_bytes=len(content),
        )

    def resolve(self, stored_name: str) -> Path:
        candidate = (self.root / stored_name).resolve()
        if candidate.parent != self.root.resolve():
            raise ValueError("Invalid storage path")
        return candidate
