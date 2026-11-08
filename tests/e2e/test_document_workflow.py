import importlib
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app


def test_complete_document_workflow(tmp_path: Path, monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    def test_db():
        with Session(engine) as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = test_db
    monkeypatch.setattr(importlib.import_module("app.main"), "engine", engine)
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "ocr_engine", "mock")
    monkeypatch.setattr(settings, "api_key", "")
    image = np.full((120, 240, 3), 255, dtype=np.uint8)
    cv2.putText(image, "FORM", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    ok, encoded = cv2.imencode(".png", image)
    assert ok

    try:
        with TestClient(app) as client:
            upload = client.post("/api/v1/documents", files={"file": ("form.png", encoded.tobytes(), "image/png")})
            assert upload.status_code == 201
            document_id = upload.json()["id"]
            processed = client.post(f"/api/v1/documents/{document_id}/process")
            assert processed.status_code == 202
            result = client.get(f"/api/v1/documents/{document_id}/extraction")
            assert result.status_code == 200
            assert result.json()["data"]["document_type"] == "unknown"
            confirmed = client.post(f"/api/v1/documents/{document_id}/confirm")
            assert confirmed.status_code == 200
            assert confirmed.json()["confirmed"] is True
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        engine.dispose()
