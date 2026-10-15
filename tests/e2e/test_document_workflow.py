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
from app.models import Base


def test_complete_document_workflow(tmp_path: Path) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    def test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    get_settings().storage_dir = str(tmp_path)
    image = np.full((120, 240, 3), 255, dtype=np.uint8)
    cv2.putText(image, "FORM", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    ok, encoded = cv2.imencode(".png", image)
    assert ok

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
