from fastapi.testclient import TestClient

from docintel.api.app import create_app
from docintel.config import Settings
from docintel.services.documents import ProductError


def test_upload_error_headers_preserve_envelope_and_request_id(tmp_path):
    app = create_app(Settings(_env_file=None, runtime_dir=tmp_path), start_worker=False)

    @app.get("/test-product-error")
    def error():
        raise ProductError(408, "UPLOAD_TIMEOUT", "safe message", headers={"Connection": "close"})

    with TestClient(app) as api:
        response = api.get("/test-product-error")
    assert response.status_code == 408
    assert response.headers["Connection"] == "close"
    assert response.json()["error"] == {
        "code": "UPLOAD_TIMEOUT",
        "message": "safe message",
        "request_id": response.headers["X-Request-ID"],
    }
