"""HTTP tests: health contract and actual framework exception handling."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from document_backend.main import create_app
from document_contracts.models import APIErrorResponse, ValidationRequest

ROOT = Path(__file__).resolve().parents[2]


def test_health_matches_shared_contract_and_reports_ocr_unavailable():
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "mock", "ocr_ready": False}
    schema = json.loads((ROOT / "schemas/v1/health-response.schema.json").read_text())
    Draft202012Validator(schema).validate(response.json())


def test_openapi_documents_only_implemented_application_routes():
    with TestClient(create_app()) as client:
        schema = client.get("/openapi.json").json()
        assert client.get("/docs").status_code == 200
    assert set(schema["paths"]) == {"/health", "/api/v1/extract"}
    operation = schema["paths"]["/health"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("HealthResponse")
    assert "500" in operation["responses"]


@pytest.mark.parametrize("payload", [
    {"schema_version": "2.0.0", "values": {}},
    {"schema_version": "1.0.0", "values": {"total_amount": 125000}},
    {"schema_version": "1.0.0", "values": {}, "secret": "synthetic-private-input"},
])
def test_invalid_request_uses_contract_envelope_without_input_echo(payload):
    app = create_app()

    # Test-only route exercises the shared handler. It is not the planned API.
    @app.post("/test-validation", response_model=ValidationRequest)
    def validate_request(body: ValidationRequest):
        return body

    with TestClient(app) as client:
        response = client.post("/test-validation", json=payload)
    assert response.status_code == 422
    result = APIErrorResponse.model_validate(response.json())
    assert result.error.code == "invalid_request"
    assert result.error.field is None
    assert "detail" not in response.json()
    assert "synthetic-private-input" not in response.text


def test_malformed_json_uses_same_error_envelope():
    app = create_app()

    @app.post("/test-validation")
    def validate_request(body: ValidationRequest):
        return body

    with TestClient(app) as client:
        response = client.post("/test-validation", content="{broken", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert APIErrorResponse.model_validate(response.json()).error.code == "invalid_request"


def test_unexpected_failure_returns_safe_500():
    app = create_app()

    @app.get("/test-failure")
    def fail():
        raise RuntimeError("synthetic-secret /private/internal/path")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-failure")
    assert response.status_code == 500
    assert APIErrorResponse.model_validate(response.json()).error.code == "internal_error"
    assert "synthetic-secret" not in response.text
    assert "/private/internal/path" not in response.text


def test_test_routes_do_not_leak_into_new_application():
    test_app = create_app()

    @test_app.get("/test-probe")
    def probe():
        return {"test_only": True}

    with TestClient(test_app) as client:
        assert client.get("/test-probe").status_code == 200
    with TestClient(create_app()) as client:
        assert client.get("/test-probe").status_code == 404
        assert "/test-probe" not in client.get("/openapi.json").json()["paths"]
