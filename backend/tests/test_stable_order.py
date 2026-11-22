"""Frozen timestamps/controlled IDs define ordering independently of insert order."""

import importlib.util
from types import SimpleNamespace

import pytest
from test_auth_api import ORIGIN, login
from test_auth_api import session_api as session_api
from test_product import image_bytes, inference, upload
from test_product import product as product

import docintel.services.documents as documents
from docintel.config import ROOT
from docintel.services.documents import DocumentService

STAMP = "2026-11-19T00:00:00+00:00"


def freeze(monkeypatch, ids):
    sequence = iter(ids)
    monkeypatch.setattr(documents, "now", lambda: STAMP)
    monkeypatch.setattr(documents, "uuid4", lambda: SimpleNamespace(hex=next(sequence)))


def listed(service):
    first = service.list_documents(2, 0)
    second = service.list_documents(2, 2)
    ids = [item.document_id for item in first.items + second.items]
    assert first.total == second.total == 3 and len(set(ids)) == 3
    assert ids == ["3" * 32, "2" * 32, "1" * 32]
    assert [item.document_id for item in service.list_documents(3, 0, "hoa_don").items] == ids
    assert service.list_documents(3, 0, "don_de_nghi").total == 0


@pytest.mark.parametrize("roundtrip", ["same_process", "restart", "backup_restore"])
def test_document_pagination_and_queue_ties_are_stable(product, monkeypatch, tmp_path, roundtrip):
    api, settings = product
    freeze(monkeypatch, ["1" * 32, "c" * 32, "3" * 32, "a" * 32, "2" * 32, "b" * 32])
    for _ in range(3):
        assert upload(api).status_code == 202
    service = api.app.state.documents
    for _ in range(3):
        listed(service)
    queued = service.list_documents(3, 0, status="queued")
    assert [item.document_id for item in queued.items] == ["3" * 32, "2" * 32, "1" * 32]
    if roundtrip == "restart":
        service = DocumentService(settings)
    elif roundtrip == "backup_restore":
        spec = importlib.util.spec_from_file_location(
            "order_backup", ROOT / "scripts/backup_runtime.py"
        )
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        backup = tmp_path.parent / (tmp_path.name + "-backup")
        restored = tmp_path.parent / (tmp_path.name + "-restore")
        helper.backup(settings.runtime_dir, backup)
        helper.restore(backup, restored)
        service = DocumentService(settings.model_copy(update={"runtime_dir": restored}))
    service.pipeline.run = inference
    processed = []
    for _ in range(3):
        assert service.process_next()
        with service.repository.transaction() as db:
            completed = {
                row["run_id"]
                for row in db.execute("SELECT run_id FROM runs WHERE status='succeeded'")
            }
        processed.append((completed - set(processed)).pop())
    assert processed == ["a" * 32, "b" * 32, "c" * 32]
    assert not service.process_next()
    listed(service)
    assert service.list_documents(3, 0, status="succeeded").total == 3


def test_run_history_tie_order_does_not_override_authoritative_latest_run(product, monkeypatch):
    api, _ = product
    freeze(monkeypatch, ["1" * 32, "c" * 32, "a" * 32, "b" * 32])
    document = upload(api).json()
    service = api.app.state.documents
    assert service.process_next()
    path = "/api/v1/documents/" + document["document_id"]
    current = "c" * 32
    for next_run in ("a" * 32, "b" * 32):
        response = api.post(path + "/runs", json={"expected_run_id": current})
        assert response.status_code == 202 and response.json()["run"]["run_id"] == next_run
        assert service.process_next()
        current = next_run
    for _ in range(3):
        history = api.get(path + "/history").json()
        assert [run["run_id"] for run in history["runs"]] == ["c" * 32, "b" * 32, "a" * 32]
    assert api.get(path).json()["run"]["run_id"] == "b" * 32
    assert api.get(path, params={"run_id": "c" * 32}).json()["is_latest_run"] is False
    assert (
        api.post(path + "/confirm", json={"run_id": "b" * 32, "expected_revision": 1}).status_code
        == 200
    )
    assert api.get(path + "/export", params={"run_id": "b" * 32, "revision": 1}).status_code == 200


def test_tied_pagination_keeps_owner_and_status_filters(session_api, monkeypatch):
    api, _ = session_api
    freeze(monkeypatch, ["1" * 32, "c" * 32, "3" * 32, "a" * 32, "2" * 32, "b" * 32])
    path = "/api/v1/documents?document_type=hoa_don&data_origin=synthetic"
    state = login(api, "alpha")
    headers = {"Origin": ORIGIN, "X-CSRF-Token": state["csrf_token"]}
    for _ in range(2):
        assert api.post(path, content=image_bytes(), headers=headers).status_code == 202
    state = login(api, "beta")
    headers["X-CSRF-Token"] = state["csrf_token"]
    assert api.post(path, content=image_bytes(), headers=headers).status_code == 202
    assert [d["document_id"] for d in api.get("/api/v1/documents").json()["items"]] == ["2" * 32]
    state = login(api, "alpha")
    pages = [
        api.get(
            "/api/v1/documents", params={"limit": 1, "offset": offset, "status": "queued"}
        ).json()
        for offset in (0, 1)
    ]
    assert [p["items"][0]["document_id"] for p in pages] == ["3" * 32, "1" * 32]
    assert all(p["total"] == 2 for p in pages)
    assert api.get("/api/v1/documents/" + "2" * 32 + "/history").status_code == 404
