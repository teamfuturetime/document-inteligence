"""Operational checks stay bounded and reveal no document/session data."""

import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from docintel import __version__
from docintel.api.app import create_app
from docintel.config import Settings
from docintel.repositories.sqlite import DocumentRepository
from docintel.services import readiness
from docintel.services.documents import DocumentService


def configured(tmp_path, **kw):
    return Settings(_env_file=None, runtime_dir=tmp_path / "runtime", **kw)


def test_readiness_before_startup_and_after_shutdown_never_initializes(tmp_path):
    settings = configured(tmp_path)
    app = create_app(settings, start_worker=False)
    api = TestClient(app)
    before = api.get("/api/v1/readiness")
    assert before.status_code == 503 and before.json()["lifecycle"] == "not_started"
    assert before.json()["database"] == "not_checked"
    assert not settings.runtime_dir.exists()
    assert api.get("/api/v1/health").json() == {"status": "ok", "app_version": __version__}
    with api:
        assert api.get("/api/v1/readiness").json()["lifecycle"] == "running"
    after = api.get("/api/v1/readiness")
    assert after.status_code == 503 and after.json()["lifecycle"] == "stopped"
    assert after.json()["database"] == "not_checked"


@pytest.mark.parametrize("mode", ["unconfigured", "fixture"])
@pytest.mark.parametrize("auth", ["local", "session"])
def test_non_native_profile_does_not_claim_product_readiness(tmp_path, mode, auth):
    settings = configured(tmp_path, provider_mode=mode, auth_mode=auth)
    with TestClient(create_app(settings, start_worker=False)) as api:
        result = api.get("/api/v1/readiness")
        assert result.status_code == 503
        report = result.json()
        assert report["database"] == "ready" and report["provider"] == mode
        assert report["worker"] == "disabled" and report["auth_mode"] == auth
        assert str(tmp_path) not in result.text
        assert result.headers["cache-control"] == "no-store"
        assert api.get("/api/v1/health").status_code == 200


def test_live_worker_ready_then_stopped_and_poll_does_not_probe_models(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(readiness, "probe", lambda *a, **k: calls.append(k) or {})
    monkeypatch.setattr(DocumentService, "process_next", lambda _: False)
    settings = configured(tmp_path, provider_mode="tesseract")
    app = create_app(settings)
    with TestClient(app) as api:
        assert len(calls) == 1 and calls[0]["timeout"] == 3

        def prohibited(*a, **kw):
            pytest.fail("poll must not initialize or probe models")

        monkeypatch.setattr(readiness, "probe", prohibited)
        monkeypatch.setattr(DocumentRepository, "initialize", prohibited)
        before = (settings.runtime_dir / "documents.sqlite3").read_bytes()
        for _ in range(5):
            result = api.get("/api/v1/readiness")
            assert result.status_code == 200 and result.json()["worker"] == "ready"
            assert result.json()["provider_check"] == "startup_snapshot"
        assert (settings.runtime_dir / "documents.sqlite3").read_bytes() == before
        app.state.inference_worker.close()
        result = api.get("/api/v1/readiness")
        assert result.status_code == 503 and result.json()["worker"] == "stopped"
        assert api.get("/api/v1/health").status_code == 200


def test_native_profile_without_worker_or_with_failed_provider_is_not_ready(tmp_path, monkeypatch):
    from document_pipeline.errors import PipelineError

    def unavailable(*a, **kw):
        raise PipelineError("PROVIDER_UNAVAILABLE", "PRIVATE_CANARY /private/models")

    monkeypatch.setattr(readiness, "probe", unavailable)
    settings = configured(tmp_path, provider_mode="tesseract")
    with TestClient(create_app(settings, start_worker=False)) as api:
        result = api.get("/api/v1/readiness")
        assert result.status_code == 503 and result.json()["provider"] == "unavailable"
        assert result.json()["worker"] == "not_started"
        assert "PRIVATE_CANARY" not in result.text and str(tmp_path) not in result.text


@pytest.mark.parametrize(
    "fault,status",
    [("missing", "unavailable"), ("corrupt", "unavailable"), ("future", "unsupported_schema")],
)
def test_live_database_faults_are_safe_without_reinitialization(
    tmp_path, monkeypatch, fault, status
):
    settings = configured(tmp_path)
    with TestClient(create_app(settings, start_worker=False)) as api:
        dbpath = settings.runtime_dir / "documents.sqlite3"
        if fault == "missing":
            dbpath.unlink()
        elif fault == "corrupt":
            dbpath.write_bytes(b"PRIVATE_CANARY corrupt database")
        else:
            with closing(sqlite3.connect(dbpath)) as db, db:
                db.execute("INSERT INTO schema_migrations VALUES(99,'future')")
        before = dbpath.read_bytes() if dbpath.exists() else None
        result = api.get("/api/v1/readiness")
        assert result.status_code == 503 and result.json()["database"] == status
        assert (dbpath.read_bytes() if dbpath.exists() else None) == before
        assert "PRIVATE_CANARY" not in result.text and str(tmp_path) not in result.text
        assert api.get("/api/v1/health").status_code == 200


def test_database_lock_is_bounded_and_recovers(tmp_path):
    DocumentRepository(tmp_path / "documents.sqlite3").initialize()
    with closing(sqlite3.connect(tmp_path / "documents.sqlite3")) as db:
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("BEGIN EXCLUSIVE")
        assert readiness.database_status(tmp_path) == "unavailable"
        db.rollback()
    assert readiness.database_status(tmp_path) == "ready"


def test_starting_and_stopping_skip_database_probe(tmp_path, monkeypatch):
    def prohibited(*_):
        pytest.fail("lifecycle transition must not touch database")

    monkeypatch.setattr(readiness, "database_status", prohibited)
    for lifecycle in ("starting", "stopping"):
        report = readiness.inspect_readiness(
            SimpleNamespace(runtime_lifecycle=lifecycle), configured(tmp_path)
        )
        assert report.status == "not_ready" and report.database == "not_checked"


def test_openapi_503_uses_readiness_contract():
    schema = create_app(Settings(_env_file=None)).openapi()
    operation = schema["paths"]["/api/v1/readiness"]["get"]
    for code in ("200", "503"):
        assert operation["responses"][code]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("/Readiness")
