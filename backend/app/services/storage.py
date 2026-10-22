"""Lưu trữ local bằng storage key; không nhận đường dẫn tùy ý từ client."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class AsyncReadable(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


class StorageSecurityError(ValueError):
    pass


class StorageService:
    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or settings.STORAGE_PATH).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, storage_key: str, *, must_exist: bool = False) -> Path:
        if not storage_key or Path(storage_key).is_absolute():
            raise StorageSecurityError("Storage key phải là tên file tương đối")
        if Path(storage_key).name != storage_key or storage_key in {".", ".."}:
            raise StorageSecurityError("Storage key không hợp lệ")
        candidate = (self.base_path / storage_key).resolve(strict=False)
        if candidate.parent != self.base_path:
            raise StorageSecurityError("Storage key nằm ngoài vùng lưu trữ")
        if must_exist and candidate.exists() and candidate.is_symlink():
            raise StorageSecurityError("Không cho phép truy cập symbolic link")
        return candidate

    def new_key(self, filename: str) -> str:
        return f"{uuid.uuid4().hex}{Path(filename).suffix.lower()}"

    def save(self, filename: str, content: bytes) -> str:
        key = self.new_key(filename)
        self._resolve(key).write_bytes(content)
        logger.info("File saved", extra={"stored_name": key, "size_bytes": len(content)})
        return key

    async def save_upload(self, upload: AsyncReadable, filename: str, max_bytes: int, *, chunk_size: int = 1024 * 1024) -> tuple[str, int, bytes]:
        key = self.new_key(filename)
        target = self._resolve(key)
        temporary = self._resolve(f"{key}.part")
        size = 0
        header = b""
        try:
            with temporary.open("xb") as stream:
                while chunk := await upload.read(chunk_size):
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError("File vượt quá giới hạn dung lượng")
                    header = (header + chunk)[:16]
                    stream.write(chunk)
            if size == 0:
                raise ValueError("File rỗng, không thể xử lý")
            os.replace(temporary, target)
            return key, size, header
        except Exception:
            temporary.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            raise

    def read(self, storage_key: str) -> bytes:
        return self._resolve(storage_key, must_exist=True).read_bytes()

    def path_for(self, storage_key: str) -> Path:
        return self._resolve(storage_key, must_exist=True)

    def delete(self, storage_key: str) -> bool:
        path = self._resolve(storage_key, must_exist=True)
        if not path.exists():
            return False
        path.unlink()
        logger.info("File deleted", extra={"stored_name": storage_key})
        return True
