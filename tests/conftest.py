"""Fixtures dùng chung cho toàn bộ test suite."""
import os
import sys
from pathlib import Path

import pytest

# Đặt DATABASE_URL thành SQLite TRƯỚC khi import app.* để test không cần PostgreSQL
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["STORAGE_PATH"] = "./storage/test_uploads"

# Thêm backend/ và ai_service/ vào sys.path để import được app.*
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
AI_DIR = Path(__file__).resolve().parents[1] / "ai_service"
for p in (BACKEND_DIR, AI_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.core.database import Base  # noqa: E402


@pytest.fixture()
def image_bytes():
    """Small real encoded images, including distinct pages for TIFF ordering."""
    from io import BytesIO
    from PIL import Image

    def encode(extension="png", pages=1, size=(80, 60), colors=None, mode="RGB", **save_options):
        formats = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP",
                   "bmp": "BMP", "tif": "TIFF", "tiff": "TIFF"}
        images = [Image.new(mode, size, (colors or ["white"])[i % len(colors or ["white"])]) for i in range(pages)]
        output = BytesIO()
        if pages > 1:
            save_options.update(save_all=True, append_images=images[1:])
        images[0].save(output, format=formats[extension], **save_options)
        return output.getvalue()

    return encode


@pytest.fixture()
def db_session():
    """Tạo database SQLite in-memory cho từng test."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()

