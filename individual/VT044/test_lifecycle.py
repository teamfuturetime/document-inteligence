from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import create_database_engine
from app.models import Base, Document, Extraction
from app.repositories.documents import DocumentRepository
from app.services.storage import LocalStorage


NOW = datetime(2026, 11, 11, 3, 0, tzinfo=timezone.utc)
TOKENS = {"demo-alice": "alice", "demo-bob": "bob"}


@pytest.fixture
def env(tmp_path):
    # Import at fixture time so the RED stage fails at the missing slice,
    # rather than silently exercising a replacement fake implementation.
    from individual.VT044.harness import Lifecycle, LifecycleService, create_app

    engine = create_database_engine(f"sqlite:///{tmp_path / 'case.db'}")
    Base.metadata.create_all(engine)
    storage = LocalStorage(tmp_path / "files")
    ids = {}
    with Session(engine) as db:
        for actor in ("alice", "bob"):
            stored = storage.save(f"Biểu mẫu {actor}.png", b"synthetic-private-" + actor.encode())
            doc = DocumentRepository(db).create(
                original_name=stored.original_name, stored_name=stored.stored_name,
                mime_type="image/png", size_bytes=stored.size_bytes,
            )
            doc.created_at = NOW
            doc.expires_at = NOW + timedelta(days=41)
            doc.status = "confirmed"
            db.add(Extraction(document_id=doc.id, data={"fields": {"name": actor}}, confirmed=True))
            db.add(Lifecycle(document_id=doc.id, owner_id=actor, deleted=False))
            ids[actor] = doc.id
        db.commit()
    service = LifecycleService(engine, storage, clock=lambda: NOW)
    with TestClient(create_app(service, TOKENS)) as client:
        yield service, client, ids
    engine.dispose()


def headers(actor="alice"):
    return {"X-API-Key": f"demo-{actor}"}


def snapshot(service, document_id):
    with Session(service.engine) as db:
        doc = db.get(Document, document_id)
        extraction = db.scalar(select(Extraction).where(Extraction.document_id == document_id))
        return (
            doc.id, doc.status, doc.expires_at, extraction.id, extraction.data,
            extraction.confirmed, sha256(service.storage.resolve(doc.stored_name).read_bytes()).hexdigest(),
        )


def test_T01_T02_T03_state_cycle_preserves_related_data(env):
    service, client, ids = env
    path = f"/documents/{ids['alice']}"
    before = snapshot(service, ids["alice"])
    assert client.get(path, headers=headers()).status_code == 200
    assert client.delete(path, headers=headers()).json() == {"id": ids["alice"], "deleted": True}
    assert client.get(path, headers=headers()).status_code == 404
    assert ids["alice"] not in client.get("/documents", headers=headers()).json()["ids"]
    for suffix in ("/content", "/extraction"):
        assert client.get(path + suffix, headers=headers()).status_code == 404
    assert snapshot(service, ids["alice"]) == before
    assert client.post(path + "/restore", headers=headers()).json() == {"id": ids["alice"], "deleted": False}
    assert client.get(path, headers=headers()).status_code == 200
    assert client.get(path + "/extraction", headers=headers()).json()["fields"]["name"] == "alice"
    assert client.get(path + "/content", headers=headers()).content == b"synthetic-private-alice"
    assert snapshot(service, ids["alice"]) == before


@pytest.mark.parametrize("action", ["delete", "restore"])
def test_T04_idempotent_commands(env, action):
    service, client, ids = env
    path = f"/documents/{ids['alice']}"
    call = (lambda: client.delete(path, headers=headers())) if action == "delete" else (
        lambda: client.post(path + "/restore", headers=headers()))
    before = snapshot(service, ids["alice"])
    assert call().status_code == 200
    assert call().json() == {"id": ids["alice"], "deleted": action == "delete"}
    assert snapshot(service, ids["alice"]) == before


@pytest.mark.parametrize("deleted", [False, True])
@pytest.mark.parametrize("method,suffix", [
    ("GET", ""), ("GET", "/content"), ("GET", "/extraction"),
    ("DELETE", ""), ("POST", "/restore"),
])
def test_T05_T06_cross_user_access_has_no_payload_or_side_effect(env, deleted, method, suffix):
    service, client, ids = env
    path = f"/documents/{ids['bob']}"
    if deleted:
        assert client.delete(path, headers=headers("bob")).status_code == 200
    before = snapshot(service, ids["bob"])
    response = client.request(method, path + suffix, headers=headers())
    assert response.status_code == 404
    assert response.json() == {"detail": "Không tìm thấy tài liệu"}
    from individual.VT044.harness import Lifecycle
    with Session(service.engine) as db:
        assert db.get(Lifecycle, ids["bob"]).deleted is deleted
    assert snapshot(service, ids["bob"]) == before


@pytest.mark.parametrize("token", [None, "invalid"])
def test_T07_missing_or_invalid_identity(env, token):
    _, client, ids = env
    supplied = {} if token is None else {"X-API-Key": token}
    assert client.delete(f"/documents/{ids['alice']}", headers=supplied).status_code == 401


def test_T08_list_is_owner_scoped(env):
    _, client, ids = env
    assert client.get("/documents", headers=headers()).json() == {"ids": [ids["alice"]]}
    assert client.get("/documents", headers=headers("bob")).json() == {"ids": [ids["bob"]]}


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_T09_expiry_boundary_and_restore(env, delta):
    service, client, ids = env
    path = f"/documents/{ids['alice']}"
    assert client.delete(path, headers=headers()).status_code == 200
    with Session(service.engine) as db:
        db.get(Document, ids["alice"]).expires_at = NOW + timedelta(seconds=delta)
        db.commit()
    response = client.post(path + "/restore", headers=headers())
    assert response.status_code == (200 if delta > 0 else 404)
    from individual.VT044.harness import Lifecycle
    with Session(service.engine) as db:
        assert db.get(Lifecycle, ids["alice"]).deleted is (delta <= 0)


@pytest.mark.parametrize("action", ["delete", "restore"])
def test_T10_processing_blocks_transition(env, action):
    service, client, ids = env
    path = f"/documents/{ids['alice']}"
    if action == "restore":
        assert client.delete(path, headers=headers()).status_code == 200
    with Session(service.engine) as db:
        db.get(Document, ids["alice"]).status = "processing"
        db.commit()
    before = snapshot(service, ids["alice"])
    response = client.delete(path, headers=headers()) if action == "delete" else client.post(path + "/restore", headers=headers())
    assert response.status_code == 409
    assert snapshot(service, ids["alice"]) == before


@pytest.mark.parametrize("action", ["delete", "restore"])
def test_T11_commit_failure_rolls_back_without_leak(env, monkeypatch, action):
    service, client, ids = env
    from individual.VT044.harness import Lifecycle
    path = f"/documents/{ids['alice']}"
    initial_deleted = action == "restore"
    if initial_deleted:
        assert client.delete(path, headers=headers()).status_code == 200
    before = snapshot(service, ids["alice"])

    def fail_commit(self):
        self.flush()  # Mutation has reached SQL; rollback must undo it.
        raise SQLAlchemyError("private-owner-bob/database-password")

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        response = client.delete(path, headers=headers()) if action == "delete" else client.post(path + "/restore", headers=headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Cơ sở dữ liệu không khả dụng"}
    with Session(service.engine) as db:
        assert db.get(Lifecycle, ids["alice"]).deleted is initial_deleted
    assert snapshot(service, ids["alice"]) == before


@pytest.mark.parametrize("method,suffix", [("GET", ""), ("DELETE", ""), ("POST", "/restore")])
def test_T12_unknown_id_is_indistinguishable_from_foreign_id(env, method, suffix):
    _, client, ids = env
    unknown = client.request(method, "/documents/missing" + suffix, headers=headers())
    foreign = client.request(method, f"/documents/{ids['bob']}" + suffix, headers=headers())
    assert (unknown.status_code, unknown.json()) == (foreign.status_code, foreign.json()) == (
        404, {"detail": "Không tìm thấy tài liệu"})


def test_T13_payload_user_id_cannot_impersonate_owner(env):
    _, client, ids = env
    response = client.delete(f"/documents/{ids['bob']}?owner_id=bob", headers={**headers(), "X-User-ID": "bob"})
    assert response.status_code == 404


def test_T14_service_enforces_owner_even_without_http(env):
    service, _, ids = env
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        service.transition("alice", ids["bob"], True)
    assert error.value.status_code == 404


def test_T15_same_document_contention_preserves_owner_and_data(env):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from fastapi import HTTPException
    from individual.VT044.harness import Lifecycle

    service, _, ids = env
    before = snapshot(service, ids["alice"])
    # Each operation creates an independent database session. Four legitimate
    # and four hostile requests contend for the same document in each phase.
    for target in (True, False):
        gate = Barrier(8, timeout=10)

        def attempt(index):
            gate.wait()
            actor = "alice" if index < 4 else "bob"
            try:
                return service.transition(actor, ids["alice"], target)
            except HTTPException as error:
                return error.status_code

        with ThreadPoolExecutor(max_workers=8) as workers:
            results = list(workers.map(attempt, range(8)))
        assert results[:4] == [{"id": ids["alice"], "deleted": target}] * 4
        assert results[4:] == [404] * 4
        with Session(service.engine) as db:
            state = db.get(Lifecycle, ids["alice"])
            assert state.owner_id == "alice"
            assert state.deleted is target
        assert snapshot(service, ids["alice"]) == before


def test_T16_missing_extraction_returns_neutral_error(env):
    from sqlalchemy import delete

    service, client, ids = env
    with Session(service.engine) as db:
        db.execute(delete(Extraction).where(Extraction.document_id == ids["alice"]))
        db.commit()
    response = client.get(f"/documents/{ids['alice']}/extraction", headers=headers())
    assert response.status_code == 404
    assert response.json() == {"detail": "Không tìm thấy tài liệu"}


def test_T17_missing_file_returns_neutral_error(env):
    service, client, ids = env
    with Session(service.engine) as db:
        doc = db.get(Document, ids["alice"])
        service.storage.resolve(doc.stored_name).unlink()
    response = client.get(f"/documents/{ids['alice']}/content", headers=headers())
    assert response.status_code == 404
    assert response.json() == {"detail": "Không tìm thấy tài liệu"}


@pytest.mark.parametrize("suffix", ["", "/content", "/extraction"])
def test_T18_expired_active_document_is_hidden_on_all_reads(env, suffix):
    service, client, ids = env
    with Session(service.engine) as db:
        db.get(Document, ids["alice"]).expires_at = NOW
        db.commit()
    response = client.get(f"/documents/{ids['alice']}" + suffix, headers=headers())
    assert response.status_code == 404
    assert response.json() == {"detail": "Không tìm thấy tài liệu"}
    assert ids["alice"] not in client.get("/documents", headers=headers()).json()["ids"]
