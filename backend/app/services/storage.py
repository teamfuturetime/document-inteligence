"""Dịch vụ lưu trữ file (local storage)."""
import shutil
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class StorageService:
    """Lưu trữ file upload vào local storage."""

    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or settings.STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: bytes) -> str:
        """Lưu nội dung file, trả về đường dẫn tương đối."""
        # Tạo tên file duy nhất để tránh trùng lặp
        ext = Path(filename).suffix.lower()
        stored_name = f"{uuid.uuid4().hex}{ext}"
        target = self.base_path / stored_name
        target.write_bytes(content)
        logger.info(
            "File saved",
            extra={"stored_name": stored_name, "size_bytes": len(content)},
        )
        return str(target)

    def read(self, relative_path: str) -> bytes:
        """Đọc nội dung file theo đường dẫn tương đối."""
        path = Path(relative_path)
        if not path.is_absolute():
            path = self.base_path / path
        return path.read_bytes()

    def delete(self, relative_path: str) -> bool:
        """Xóa file theo đường dẫn tương đối."""
        path = Path(relative_path)
        if not path.is_absolute():
            path = self.base_path / path
        if path.exists():
            path.unlink()
            logger.info("File deleted", extra={"path": str(path)})
            return True
        return False

    def delete_directory(self, directory: str) -> None:
        """Xóa toàn bộ thư mục lưu trữ (dùng cho retention)."""
        path = Path(directory)
        if path.exists() and path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
