import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from document_pipeline.errors import PipelineError
from document_pipeline.models import InferenceResult, Prediction, Token
from fastapi.testclient import TestClient
from PIL import Image

import docintel.services.documents as document_module
from docintel.api.app import create_app
from docintel.config import Settings
from docintel.services.documents import DocumentService

INVOICE = {
    "invoice_number": "0000123",
    "invoice_date": "2026-10-24",
    "seller_name": "Công ty Mẫu",
    "total_amount": 1250000,
    "currency": "VND",
}


def image_bytes(color="white"):
    stream = io.BytesIO()
    Image.new("RGB", (300, 200), color).save(stream, format="PNG")
    return stream.getvalue()


def inference(data, document_type):
    return InferenceResult(
        pipeline_version="unit-test",
        document_type=document_type,
        image_width=300,
        image_height=200,
        tokens=(
            Token(
                token_id="w0",
                line_id="0",
                text="source",
                box=(0.0, 0.0, 10.0, 10.0),
                confidence=0.9,
            ),
        ),
        fields=tuple(
            Prediction(
                field_id=key,
                raw_value=str(value),
                normalized_value=value,
                observation="found",
                evidence_token_ids=("w0",),
                ocr_score=0.9,
                candidate_count=1,
            )
            for key, value in INVOICE.items()
        ),
        warnings=(),
        metadata={"confidence_version": "unit-test-explicit", "prediction_source": "model"},
    )


@pytest.fixture
def product(tmp_path, monkeypatch):
    # This is a workflow unit-test double, never benchmark evidence.
    monkeypatch.setattr(DocumentService, "ensure_ready", lambda self: {})
    settings = Settings(_env_file=None, provider_mode="tesseract", runtime_dir=tmp_path)
    with TestClient(create_app(settings, start_worker=False)) as api:
        monkeypatch.setattr(api.app.state.documents.pipeline, "run", inference)
        yield api, settings


def upload(api, *, key=None, content=None):
    return api.post(
        "/api/v1/documents",
        params={
            "document_type": "hoa_don",
            "data_origin": "synthetic",
            "filename": "../../sample.png",
        },
        headers={"Idempotency-Key": key} if key else {},
        content=image_bytes() if content is None else content,
    )


def processed(api):
    response = upload(api)
    assert response.status_code == 202, response.text
    document = response.json()
    assert api.app.state.documents.process_next()
    return api.get("/api/v1/documents/" + document["document_id"]).json()


def revision_request(document, number=None):
    return {
        "run_id": document["run"]["run_id"],
        "expected_revision": number or document["review"]["revision"],
    }


def test_real_workflow_authority_and_persistence(product):
    api, settings = product
    document = processed(api)
    path = "/api/v1/documents/" + document["document_id"]
    assert document["filename"] == "sample.png"
    assert document["review"]["effective_data"] == INVOICE
    assert (
        api.get(
            path + "/export", params={"run_id": document["run"]["run_id"], "revision": 1}
        ).status_code
        == 409
    )
    assert (
        api.post(
            path + "/confirm", json={**revision_request(document), "approved": True}
        ).status_code
        == 422
    )
    confirmed = api.post(path + "/confirm", json=revision_request(document))
    assert confirmed.status_code == 200
    exported = api.get(
        path + "/export", params={"run_id": document["run"]["run_id"], "revision": 1}
    )
    assert exported.status_code == 200
    assert exported.json()["data"] == INVOICE
    assert exported.json()["provenance"] == {
        "data_origin": "synthetic",
        "prediction_source": "model",
    }
    assert "attachment" in exported.headers["content-disposition"]
    assert "runtime" not in exported.text
    assert api.get(path + "/image").headers["content-type"] == "image/png"
    with TestClient(create_app(settings, start_worker=False)) as restarted:
        assert restarted.get(path).json()["review"]["review_status"] == "confirmed"
        assert (
            restarted.get(
                path + "/export", params={"run_id": document["run"]["run_id"], "revision": 1}
            ).status_code
            == 200
        )


def test_clear_null_and_revision_conflict(product):
    api, _ = product
    document = processed(api)
    path = "/api/v1/documents/" + document["document_id"]
    saved = api.put(
        path + "/review",
        json={
            **revision_request(document),
            "fields": {
                "seller_name": {"is_reviewed": True, "reviewed_value": None},
            },
        },
    )
    assert saved.status_code == 200
    value = api.get(path).json()
    assert value["review"]["effective_data"]["seller_name"] is None
    assert (
        next(field for field in value["run"]["fields"] if field["field_id"] == "seller_name")[
            "normalized_value"
        ]
        == INVOICE["seller_name"]
    )
    assert api.post(path + "/confirm", json=revision_request(value)).status_code == 422
    assert api.post(path + "/confirm", json=revision_request(document)).status_code == 409
    assert (
        api.put(path + "/review", json={**revision_request(document), "fields": {}}).status_code
        == 409
    )
    assert (
        api.get(
            path + "/export", params={"run_id": document["run"]["run_id"], "revision": 1}
        ).status_code
        == 409
    )
    corrected = api.put(
        path + "/review",
        json={
            **revision_request(value),
            "fields": {
                "seller_name": {"is_reviewed": True, "reviewed_value": "Đơn vị đã sửa"},
            },
        },
    ).json()
    assert api.post(path + "/confirm", json=revision_request(corrected)).status_code == 200
    assert (
        api.put(
            path + "/review",
            json={
                **revision_request(corrected),
                "expected_status": "confirmed",
                "fields": {
                    "total_amount": {"is_reviewed": True, "reviewed_value": "0"},
                },
            },
        ).json()["review"]["review_status"]
        == "draft"
    )


def test_concurrent_saves_compare_and_swap(product):
    api, _ = product
    document = processed(api)
    path = "/api/v1/documents/" + document["document_id"] + "/review"

    def save(value):
        return api.put(
            path,
            json={
                **revision_request(document),
                "fields": {
                    "seller_name": {"is_reviewed": True, "reviewed_value": value},
                },
            },
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, ("A", "B"))) == [200, 409]


def test_autosave_cannot_reopen_after_other_tab_confirms(product):
    api, _ = product
    document = processed(api)
    path = "/api/v1/documents/" + document["document_id"]
    assert api.post(path + "/confirm", json=revision_request(document)).status_code == 200
    body = {
        **revision_request(document),
        "expected_status": "draft",
        "fields": {"seller_name": {"is_reviewed": True, "reviewed_value": "late autosave"}},
    }
    rejected = api.put(path + "/review", json=body)
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "REVIEW_STATE_CONFLICT"
    assert api.get(path).json()["review"]["review_status"] == "confirmed"
    exported = api.get(path + "/export", params={"run_id": body["run_id"], "revision": 1})
    assert exported.status_code == 200
    assert exported.json()["data"]["seller_name"] == INVOICE["seller_name"]
    body["expected_status"] = "confirmed"
    reopened = api.put(path + "/review", json=body)
    assert reopened.status_code == 200
    assert reopened.json()["review"]["review_status"] == "draft"
    assert reopened.json()["review"]["revision"] == 2
    assert api.put(path + "/review", json=body).status_code == 409


def test_reprocess_keeps_previous_machine_and_review(product):
    api, _ = product
    old = processed(api)
    path = "/api/v1/documents/" + old["document_id"]
    api.post(path + "/confirm", json=revision_request(old))
    response = api.post(path + "/runs", json={"expected_run_id": old["run"]["run_id"]})
    assert response.status_code == 202
    assert response.json()["run"]["run_id"] != old["run"]["run_id"]
    assert (
        api.get(path, params={"run_id": old["run"]["run_id"]}).json()["review"]["review_status"]
        == "confirmed"
    )
    assert (
        api.get(
            path + "/export", params={"run_id": old["run"]["run_id"], "revision": 1}
        ).status_code
        == 409
    )
    assert api.app.state.documents.process_next()
    current = api.get(path).json()
    assert current["review"]["revision"] == 1
    history = api.get(path + "/history").json()
    assert len(history["runs"]) == 2
    assert any(event["action"] == "confirmed" for event in history["events"])


def test_upload_limits_idempotency_queue_and_safe_errors(product):
    api, _ = product
    first = upload(api, key="same-key")
    assert first.status_code == 202
    assert upload(api, key="same-key").json()["document_id"] == first.json()["document_id"]
    assert upload(api, key="same-key", content=b"different").status_code == 409
    assert upload(api, content=b"not an image").status_code == 415
    assert upload(api, content=b"x" * (5_242_880 + 1)).status_code == 413
    assert (
        api.post(
            "/api/v1/documents?document_type=hoa_don&data_origin=real", content=image_bytes()
        ).status_code
        == 422
    )
    api.app.state.documents.settings.max_pending_runs = 1
    response = upload(api)
    assert response.status_code == 429
    files = list(api.app.state.documents.storage.root.iterdir())
    assert len(files) == 2  # Rejected upload left no orphan source/preview.
    assert api.get("/api/v1/documents/unknown/image").status_code == 404
    assert (
        api.post("/api/v1/documents", headers={"Origin": "https://untrusted.example"}).status_code
        == 403
    )


@pytest.mark.parametrize(("second_color", "expected_status"), [("white", 202), ("black", 409)])
def test_concurrent_upload_retries_when_queue_fills(
    product, monkeypatch, second_color, expected_status
):
    api, settings = product
    settings.max_pending_runs = 1
    service = api.app.state.documents
    barrier = threading.Barrier(2, timeout=15)
    prepare_image = document_module.prepare_image

    def prepare_concurrent_image(data, config):
        page = prepare_image(data, config)
        # Both requests have missed the initial key lookup before either can admit a run.
        barrier.wait()
        return page

    monkeypatch.setattr(document_module, "prepare_image", prepare_concurrent_image)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(upload, api, key="race", content=image_bytes(color))
            for color in ("white", second_color)
        ]
        responses = [future.result(timeout=20) for future in futures]

    assert sorted(response.status_code for response in responses) == [202, expected_status]
    admitted = [response.json() for response in responses if response.status_code == 202]
    assert len({item["document_id"] for item in admitted}) == 1
    assert len({item["run"]["run_id"] for item in admitted}) == 1
    assert api.get("/api/v1/documents").json()["total"] == 1
    history = api.get(f"/api/v1/documents/{admitted[0]['document_id']}/history").json()
    assert len(history["runs"]) == 1
    assert [event["action"] for event in history["events"]] == ["uploaded"]
    assert len(list(service.storage.root.iterdir())) == 2


def test_provider_failure_never_falls_back_and_restart_recovery(product, monkeypatch):
    api, _ = product
    document = upload(api).json()

    def failed(*args):
        raise PipelineError("PROVIDER_UNAVAILABLE", "private path must not leak")

    monkeypatch.setattr(api.app.state.documents.pipeline, "run", failed)
    assert api.app.state.documents.process_next()
    response = api.get("/api/v1/documents/" + document["document_id"])
    assert response.json()["run"]["status"] == "unavailable"
    assert response.json()["review"] is None
    assert "private path" not in response.text
    queued = upload(api).json()
    repository = api.app.state.documents.repository
    with repository.transaction(write=True) as connection:
        connection.execute(
            "UPDATE runs SET status='running' WHERE run_id=?", (queued["run"]["run_id"],)
        )
    api.app.state.documents.recover_interrupted()
    assert (
        api.get("/api/v1/documents/" + queued["document_id"]).json()["run"]["error_code"]
        == "PROCESSING_INTERRUPTED"
    )


def test_source_integrity_and_history_not_overwritten(product):
    api, _ = product
    document = upload(api).json()
    service = api.app.state.documents
    service.storage.path(document["document_id"], "source").write_bytes(b"corrupt")
    assert service.process_next()
    assert (
        api.get("/api/v1/documents/" + document["document_id"]).json()["run"]["error_code"]
        == "INPUT_CHANGED"
    )


def test_foreign_schema_fields_and_invalid_types(product):
    api, _ = product
    document = processed(api)
    path = "/api/v1/documents/" + document["document_id"] + "/review"
    for value in (True, [], {}):
        assert (
            api.put(
                path,
                json={
                    **revision_request(document),
                    "fields": {
                        "seller_name": {"is_reviewed": True, "reviewed_value": value},
                    },
                },
            ).status_code
            == 422
        )
    assert (
        api.put(
            path,
            json={
                **revision_request(document),
                "fields": {
                    "full_name": {"is_reviewed": True, "reviewed_value": "foreign"},
                },
            },
        ).status_code
        == 422
    )
    assert (
        api.put(
            path,
            json={
                **revision_request(document),
                "fields": {
                    "seller_name": {"is_reviewed": False, "reviewed_value": "not allowed"},
                },
            },
        ).status_code
        == 422
    )


def test_pagination_filters_and_operational_metrics(product):
    api, _ = product
    one = processed(api)
    processed(api)
    page = api.get("/api/v1/documents?limit=1&offset=1&status=succeeded").json()
    assert page["total"] == 2 and len(page["items"]) == 1
    path = "/api/v1/documents/" + one["document_id"]
    edited = api.put(
        path + "/review",
        json={
            **revision_request(one),
            "fields": {
                "total_amount": {"is_reviewed": True, "reviewed_value": 0},
            },
        },
    ).json()
    assert api.post(path + "/confirm", json=revision_request(edited)).status_code == 200
    metrics = api.get("/api/v1/insights").json()
    assert metrics["documents"] == 2
    assert metrics["corrected_fields"] == 1
    assert metrics["confirmed_documents"] == 1
    assert "accuracy" not in json.dumps(metrics)


def test_backup_restore_preserves_reviews_and_checks_integrity(product, tmp_path):
    import importlib.util

    from docintel.config import ROOT

    spec = importlib.util.spec_from_file_location(
        "backup_runtime", ROOT / "scripts/backup_runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    api, settings = product
    document = processed(api)
    api.post(
        "/api/v1/documents/" + document["document_id"] + "/confirm", json=revision_request(document)
    )
    destination = tmp_path.parent / (tmp_path.name + "-backup")
    restored = tmp_path.parent / (tmp_path.name + "-restore")
    module.backup(settings.runtime_dir, destination)
    module.restore(destination, restored)
    with TestClient(
        create_app(settings.model_copy(update={"runtime_dir": restored}), start_worker=False)
    ) as clone:
        detail = clone.get("/api/v1/documents/" + document["document_id"]).json()
        assert detail["review"]["review_status"] == "confirmed"
    with pytest.raises(FileExistsError):
        module.restore(destination, restored)
    (destination / "documents.sqlite3").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        module.restore(destination, tmp_path.parent / (tmp_path.name + "-bad-restore"))


def test_worker_lock_and_newer_database_schema_rejected(tmp_path):
    from docintel.repositories.locking import RuntimeLock
    from docintel.repositories.sqlite import DocumentRepository

    first, second = RuntimeLock(tmp_path / "worker.lock"), RuntimeLock(tmp_path / "worker.lock")
    first.acquire()
    try:
        with pytest.raises(RuntimeError, match="worker"):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()
    repository = DocumentRepository(tmp_path / "future.sqlite3")
    repository.initialize()
    with repository.transaction(write=True) as connection:
        connection.execute("INSERT INTO schema_migrations VALUES(2,'future')")
    with pytest.raises(RuntimeError, match="newer"):
        repository.initialize()


@pytest.mark.parametrize("status_field", [{}, {"expected_status": None}])
def test_legacy_status_cannot_reopen_confirmed(product, status_field):
    api, _ = product
    document = processed(api)
    path = "/api/v1/documents/" + document["document_id"]
    assert api.post(path + "/confirm", json=revision_request(document)).status_code == 200
    result = api.put(
        path + "/review",
        json={
            **revision_request(document),
            **status_field,
            "fields": {"seller_name": {"is_reviewed": True, "reviewed_value": "late legacy write"}},
        },
    )
    assert result.status_code == 409
    assert api.get(path).json()["review"]["review_status"] == "confirmed"
    exported = api.get(
        path + "/export", params={"run_id": document["run"]["run_id"], "revision": 1}
    )
    assert exported.status_code == 200
    assert exported.json()["data"] == INVOICE
