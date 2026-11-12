"""VT-042: async admission/retry contract with real SQLite and file storage.

Provider/decode doubles isolate the workflow; these tests do not measure OCR accuracy.
"""

import io
import itertools
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from document_pipeline.errors import PipelineError
from fastapi.testclient import TestClient
from PIL import Image

import docintel.services.documents as document_module
from docintel.api.app import create_app
from docintel.config import Settings
from docintel.services.documents import DocumentService, ProductError

FACTORS = (
    ("kind", ("hoa_don", "don_de_nghi")),
    ("key", ("same", "new")),
    ("payload", ("same", "different")),
    ("queue", ("free", "full")),
)
COMBINATIONS = tuple(itertools.product(*(values for _, values in FACTORS)))


def pairs(row):
    return {
        (left, row[left], right, row[right]) for left, right in itertools.combinations(range(4), 2)
    }


def covering_array():
    uncovered = set().union(*(pairs(row) for row in COMBINATIONS))
    selected = []
    while uncovered:
        # max() keeps the first row on ties: the predefined product order is deterministic.
        row = max(COMBINATIONS, key=lambda candidate: len(pairs(candidate) & uncovered))
        selected.append(row)
        uncovered -= pairs(row)
    return tuple(selected)


PAIRWISE = covering_array()


def png(color="white"):
    stream = io.BytesIO()
    Image.new("RGB", (12, 12), color).save(stream, format="PNG")
    return stream.getvalue()


@pytest.fixture
def workflow(tmp_path, monkeypatch):
    monkeypatch.setattr(DocumentService, "ensure_ready", lambda self: {"test_double": True})
    monkeypatch.setattr(
        document_module,
        "prepare_image",
        lambda data, config: SimpleNamespace(png=data, width=12, height=12),
    )
    settings = Settings(
        _env_file=None, provider_mode="tesseract", runtime_dir=tmp_path, max_pending_runs=2
    )
    with TestClient(create_app(settings, start_worker=False)) as api:
        yield api, api.app.state.documents, settings


def upload(api, key="K", data=None, kind="hoa_don", origin="synthetic"):
    return api.post(
        "/api/v1/documents",
        params={"document_type": kind, "data_origin": origin, "filename": "sample.png"},
        headers={"Idempotency-Key": key},
        content=png() if data is None else data,
    )


def counts(service):
    with service.repository.transaction() as connection:
        return tuple(
            connection.execute("SELECT count(*) FROM " + table).fetchone()[0]
            for table in ("documents", "runs", "events", "revisions")
        )


def stored_files(settings):
    return tuple(sorted(path.name for path in (settings.runtime_dir / "documents").glob("*")))


def test_pairwise_covers_every_value_pair():
    expected = set().union(*(pairs(row) for row in COMBINATIONS))
    actual = set().union(*(pairs(row) for row in PAIRWISE))
    assert len(expected) == 24 and actual == expected
    assert len(PAIRWISE) == 6 < len(COMBINATIONS) == 16


@pytest.mark.parametrize(
    "kind,key,payload,queue",
    PAIRWISE,
    ids=[f"PW{number:02}-" + "-".join(row) for number, row in enumerate(PAIRWISE, 1)],
)
def test_pairwise_retry_contract(workflow, kind, key, payload, queue):
    api, service, settings = workflow
    first = upload(api, kind=kind)
    assert first.status_code == 202
    settings.max_pending_runs = 1 if queue == "full" else 2
    response = upload(
        api,
        "K" if key == "same" else "K2",
        png("black") if payload == "different" else png(),
        kind,
    )
    expected = (
        409
        if key == "same" and payload == "different"
        else (202 if key == "same" or queue == "free" else 429)
    )
    assert response.status_code == expected, response.text
    total = 2 if expected == 202 and key == "new" else 1
    assert counts(service) == (total, total, total, 0)
    assert len(stored_files(settings)) == 2 * total
    if expected == 202 and key == "same":
        assert response.json()["document_id"] == first.json()["document_id"]
        assert response.json()["run"]["run_id"] == first.json()["run"]["run_id"]


def test_w1_retry_replays_ids_without_duplicate_records_or_files(workflow):
    api, service, settings = workflow
    first, retry = upload(api), upload(api)
    assert first.status_code == retry.status_code == 202
    assert first.json()["document_id"] == retry.json()["document_id"]
    assert first.json()["run"]["run_id"] == retry.json()["run"]["run_id"]
    assert counts(service) == (1, 1, 1, 0)
    assert len(stored_files(settings)) == 2


def test_w2_conflicting_retry_cannot_mutate_the_original(workflow):
    api, service, settings = workflow
    original = upload(api).json()
    files_before = stored_files(settings)
    response = upload(api, data=png("black"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    current = api.get("/api/v1/documents/" + original["document_id"]).json()
    assert current["input_sha256"] == original["input_sha256"]
    assert current["run"]["run_id"] == original["run"]["run_id"]
    assert counts(service) == (1, 1, 1, 0) and stored_files(settings) == files_before


def forced_race(workflow, monkeypatch, *, different_payload=False):
    api, _, settings = workflow
    settings.max_pending_runs = 1
    barrier = threading.Barrier(2, timeout=8)
    original = document_module.prepare_image

    def prepared(data, config):
        result = original(data, config)
        barrier.wait()  # Both requests must have missed the initial key lookup.
        return result

    monkeypatch.setattr(document_module, "prepare_image", prepared)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(upload, api, "RACE", png("black") if i and different_payload else png())
            for i in range(2)
        ]
        return [future.result(timeout=15) for future in futures]


def test_concurrent_retry_at_full_capacity_replays_the_winner(workflow, monkeypatch):
    responses = forced_race(workflow, monkeypatch)
    assert sorted(response.status_code for response in responses) == [202, 202]
    assert len({response.json()["document_id"] for response in responses}) == 1
    assert len({response.json()["run"]["run_id"] for response in responses}) == 1
    assert counts(workflow[1]) == (1, 1, 1, 0)
    assert len(stored_files(workflow[2])) == 2


def test_concurrent_conflicting_key_at_capacity_returns_conflict(workflow, monkeypatch):
    responses = forced_race(workflow, monkeypatch, different_payload=True)
    assert sorted(response.status_code for response in responses) == [202, 409]
    assert counts(workflow[1]) == (1, 1, 1, 0)
    assert len(stored_files(workflow[2])) == 2


@pytest.mark.parametrize("delta,expected", [(-1, 202), (0, 202), (1, 413)])
def test_upload_byte_boundary_is_inclusive(workflow, delta, expected):
    api, service, settings = workflow
    data = png()
    settings.max_upload_bytes = len(data) - delta
    response = upload(api, data=data)
    assert response.status_code == expected
    assert counts(service) == ((1, 1, 1, 0) if expected == 202 else (0, 0, 0, 0))


def test_invalid_key_is_rejected_before_side_effects(workflow):
    api, service, settings = workflow
    assert upload(api, "bad key!").status_code == 422
    assert counts(service) == (0, 0, 0, 0) and stored_files(settings) == ()


def test_full_queue_rejects_a_new_key_without_side_effects(workflow):
    api, service, settings = workflow
    settings.max_pending_runs = 1
    assert upload(api).status_code == 202
    files_before = stored_files(settings)
    response = upload(api, "OTHER")
    assert response.status_code == 429 and response.json()["error"]["code"] == "QUEUE_FULL"
    assert counts(service) == (1, 1, 1, 0) and stored_files(settings) == files_before


def test_failed_worker_retry_keeps_the_original_run(workflow, monkeypatch):
    api, service, _ = workflow
    document = upload(api).json()

    def timeout(*args):
        raise PipelineError("OCR_TIMEOUT", "controlled workflow test")

    monkeypatch.setattr(service.pipeline, "run", timeout)
    assert service.process_next()
    current = api.get("/api/v1/documents/" + document["document_id"]).json()
    assert current["run"]["status"] == "failed" and current["run"]["error_code"] == "OCR_TIMEOUT"
    retry = upload(api)
    assert retry.status_code == 202
    assert retry.json()["run"]["run_id"] == document["run"]["run_id"]
    assert counts(service) == (1, 1, 2, 0) and not service.process_next()


def test_running_status_is_readable_before_inference_finishes(workflow, monkeypatch):
    api, service, _ = workflow
    document = upload(api).json()
    entered, release = threading.Event(), threading.Event()

    def inference(*args):
        entered.set()
        assert release.wait(8)
        raise PipelineError("OCR_TIMEOUT", "controlled workflow test")

    monkeypatch.setattr(service.pipeline, "run", inference)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(service.process_next)
        try:
            assert entered.wait(8)
            response = api.get("/api/v1/documents/" + document["document_id"])
            assert response.json()["run"]["status"] == "running"
        finally:
            release.set()
        assert future.result(timeout=10)
    assert (
        api.get("/api/v1/documents/" + document["document_id"]).json()["run"]["status"] == "failed"
    )


def test_preview_write_failure_cleans_source_then_retry_succeeds(workflow, monkeypatch):
    api, service, settings = workflow
    original = service.storage.write

    def fail_preview(document_id, kind, data):
        if kind == "preview":
            raise OSError("controlled preview write failure")
        return original(document_id, kind, data)

    monkeypatch.setattr(service.storage, "write", fail_preview)
    with pytest.raises(OSError, match="controlled preview"):
        service.upload(png(), "hoa_don", "synthetic", "sample.png", "IO")
    assert counts(service) == (0, 0, 0, 0) and stored_files(settings) == ()
    monkeypatch.setattr(service.storage, "write", original)
    assert upload(api, "IO").status_code == 202
    assert counts(service) == (1, 1, 1, 0) and len(stored_files(settings)) == 2


def test_restart_preserves_queued_and_marks_interrupted_running(workflow):
    api, service, settings = workflow
    queued, running = upload(api, "A").json(), upload(api, "B").json()
    with service.repository.transaction(write=True) as connection:
        connection.execute(
            "UPDATE runs SET status='running' WHERE run_id=?", (running["run"]["run_id"],)
        )
    reopened = DocumentService(settings)
    reopened.recover_interrupted()
    assert reopened.detail(queued["document_id"]).run.status == "queued"
    assert reopened.detail(running["document_id"]).run.error_code == "PROCESSING_INTERRUPTED"
    assert counts(reopened) == (2, 2, 3, 0)


def test_retry_after_lost_response_reuses_the_committed_upload(workflow):
    api, service, settings = workflow
    dropped = False

    def lose_ack(response):
        nonlocal dropped
        if not dropped and response.request.method == "POST":
            dropped = True
            raise ConnectionError("controlled ACK loss after endpoint commit")

    api.event_hooks["response"].append(lose_ack)
    with pytest.raises(ConnectionError, match="ACK loss"):
        upload(api, "LOST_ACK")
    assert counts(service) == (1, 1, 1, 0)
    with service.repository.transaction() as connection:
        row = connection.execute(
            "SELECT document_id,latest_run_id FROM documents WHERE idempotency_key='LOST_ACK'"
        ).fetchone()
    retry = upload(api, "LOST_ACK")
    assert retry.status_code == 202
    assert (retry.json()["document_id"], retry.json()["run"]["run_id"]) == tuple(row)
    assert counts(service) == (1, 1, 1, 0) and len(stored_files(settings)) == 2


@pytest.mark.parametrize("change", [{"kind": "don_de_nghi"}, {"origin": "sample"}])
def test_key_fingerprint_also_includes_schema_and_origin(workflow, change):
    api, service, settings = workflow
    original = upload(api).json()
    response = upload(api, **change)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert counts(service) == (1, 1, 1, 0) and len(stored_files(settings)) == 2
    assert api.get("/api/v1/documents/" + original["document_id"]).json()["run"] == original["run"]


def test_provider_unavailable_does_not_admit_or_create_files(workflow, monkeypatch):
    api, service, settings = workflow

    def unavailable():
        raise ProductError(503, "PROVIDER_UNAVAILABLE", "controlled provider failure")

    monkeypatch.setattr(service, "ensure_ready", unavailable)
    response = upload(api)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert counts(service) == (0, 0, 0, 0) and stored_files(settings) == ()
