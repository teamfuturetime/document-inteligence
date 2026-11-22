"""I/O faults keep HTTP admission, durable state and cleanup outcomes consistent."""

import asyncio
import errno
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest
from test_auth_api import ORIGIN, login
from test_auth_api import session_api as session_api
from test_upload_ingress import app_for, body, png, post

from docintel.services.documents import ProductError
from docintel.storage.local import LocalDocumentStorage


def row_counts(service):
    with service.repository.transaction() as db:
        return [
            db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("documents", "runs", "events")
        ]


@pytest.mark.parametrize(
    "fault",
    ["source", "permission", "preview", "fsync", "commit", "integrity", "cleanup", "commit_ack"],
)
def test_http_storage_faults_release_slot_and_retry_same_key(tmp_path, monkeypatch, caplog, fault):
    app = app_for(tmp_path, monkeypatch, max_concurrent_uploads=1, max_pending_runs=1)

    async def run():
        async with app.router.lifespan_context(app):
            service = app.state.documents
            fired = False
            original_write = service.storage.write
            original_transaction = service.repository.transaction

            def write(document_id, kind, data):
                nonlocal fired
                if not fired and (
                    (fault in {"source", "permission"} and kind == "source")
                    or (fault in {"preview", "cleanup"} and kind == "preview")
                ):
                    fired = True
                    if fault == "permission":
                        raise PermissionError(errno.EACCES, "PRIVATE_CANARY /sensitive/source")
                    if fault == "source":
                        original_write(document_id, kind, data)
                    raise OSError(errno.ENOSPC, "PRIVATE_CANARY /sensitive/preview")
                return original_write(document_id, kind, data)

            monkeypatch.setattr(service.storage, "write", write)
            original_discard = service.storage.discard
            if fault == "cleanup":

                def discard(_):
                    raise PermissionError("PRIVATE_CANARY cleanup path")

                monkeypatch.setattr(service.storage, "discard", discard)

            @contextmanager
            def transaction(*, write=False):
                nonlocal fired
                with original_transaction(write=write) as db:
                    yield db
                    if write and not fired and fault in {"commit", "integrity"}:
                        fired = True
                        error = (
                            sqlite3.IntegrityError
                            if fault == "integrity"
                            else sqlite3.OperationalError
                        )
                        raise error("PRIVATE_CANARY SQL commit")
                if write and not fired and fault == "commit_ack":
                    fired = True
                    raise sqlite3.OperationalError("PRIVATE_CANARY lost commit acknowledgement")

            monkeypatch.setattr(service.repository, "transaction", transaction)
            if fault == "fsync":
                import docintel.storage.local as storage

                original_fsync = storage.os.fsync

                def fsync(fd):
                    nonlocal fired
                    if not fired:
                        fired = True
                        raise OSError(errno.ENOSPC, "PRIVATE_CANARY fsync")
                    return original_fsync(fd)

                monkeypatch.setattr(storage.os, "fsync", fsync)
            headers = [(b"idempotency-key", b"fault-retry")]
            status, payload, response_headers, _ = await post(app, [body(png())], headers)
            assert status == 500 and payload["error"]["code"] == "INTERNAL_ERROR"
            assert payload["error"]["request_id"] == response_headers[b"x-request-id"].decode()
            assert "PRIVATE_CANARY" not in str(payload) and "PRIVATE_CANARY" not in caplog.text
            assert app.state.upload_limiter.borrowed_tokens == 0
            assert row_counts(service) == ([1, 1, 1] if fault == "commit_ack" else [0, 0, 0])
            if fault == "cleanup":
                assert "cleanup failed" in caplog.text
                monkeypatch.setattr(service.storage, "discard", original_discard)
            elif fault != "commit_ack":
                assert list(service.storage.root.iterdir()) == []
            retry = await post(app, [body(png())], headers)
            assert retry[0] == 202 and row_counts(service) == [1, 1, 1]
            document_id = retry[1]["document_id"]
            assert service.storage.path(document_id, "source").read_bytes() == png()
            assert service.storage.path(document_id, "preview").is_file()
            assert (await post(app, [body(png())], headers))[1]["document_id"] == document_id
            assert row_counts(service) == [1, 1, 1]

    asyncio.run(run())


def test_cleanup_does_not_mask_original_error(tmp_path, monkeypatch, caplog):
    from docintel.config import Settings
    from docintel.services.documents import DocumentService

    service = DocumentService(Settings(_env_file=None, runtime_dir=tmp_path))
    monkeypatch.setattr(service, "ensure_ready", lambda: {})
    root = OSError(errno.ENOSPC, "PRIVATE_CANARY root")

    def write(*_):
        raise root

    def cleanup(*_):
        raise PermissionError("PRIVATE_CANARY cleanup")

    monkeypatch.setattr(service.storage, "write", write)
    monkeypatch.setattr(service.storage, "discard", cleanup)
    with pytest.raises(ProductError) as failure:
        service.upload(png(), "hoa_don", "synthetic", "test.png", "key")
    assert failure.value.__cause__ is root
    assert failure.value.code == "INTERNAL_ERROR"
    assert "cleanup failed" in caplog.text and "PRIVATE_CANARY" not in caplog.text


def test_discard_attempts_both_assets_when_first_unlink_fails(tmp_path, monkeypatch):
    storage = LocalDocumentStorage(tmp_path)
    document_id = "a" * 32
    storage.write(document_id, "source", b"source")
    storage.write(document_id, "preview", b"preview")
    original = Path.unlink

    def unlink(path, *a, **kw):
        if path.suffix == ".source":
            raise PermissionError("synthetic failure")
        return original(path, *a, **kw)

    monkeypatch.setattr(Path, "unlink", unlink)
    with pytest.raises(PermissionError):
        storage.discard(document_id)
    assert storage.path(document_id, "source").exists()
    assert not storage.path(document_id, "preview").exists()


def test_cancelled_http_keeps_slot_until_failed_persistence_finishes(tmp_path, monkeypatch):
    import threading

    app = app_for(tmp_path, monkeypatch, max_concurrent_uploads=1)
    entered, release = threading.Event(), threading.Event()

    async def run():
        async with app.router.lifespan_context(app):
            original = app.state.documents.storage.write

            def blocked(document_id, kind, data):
                if kind == "source":
                    original(document_id, kind, data)
                    entered.set()
                    assert release.wait(5)
                    raise OSError(errno.ENOSPC, "synthetic write failure")
                return original(document_id, kind, data)

            monkeypatch.setattr(app.state.documents.storage, "write", blocked)
            request = asyncio.create_task(post(app, [body(png())]))
            try:
                assert await asyncio.to_thread(entered.wait, 2)
                request.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await request
                assert app.state.upload_limiter.borrowed_tokens == 1
                assert (await post(app, []))[0] == 429
            finally:
                release.set()
                await asyncio.wait_for(
                    asyncio.gather(*app.state.upload_tasks, return_exceptions=True), 3
                )
            assert app.state.upload_limiter.borrowed_tokens == 0
            assert row_counts(app.state.documents) == [0, 0, 0]
            assert list(app.state.documents.storage.root.iterdir()) == []
            monkeypatch.setattr(app.state.documents.storage, "write", original)
            assert (await post(app, [body(png())]))[0] == 202

    asyncio.run(run())


def test_unknown_commit_outcome_retains_assets_and_original_cause(tmp_path, monkeypatch, caplog):
    from docintel.config import Settings
    from docintel.services.documents import DocumentService

    service = DocumentService(Settings(_env_file=None, runtime_dir=tmp_path))
    monkeypatch.setattr(service, "ensure_ready", lambda: {})
    original = service.repository.transaction
    failed = False
    root = sqlite3.OperationalError("PRIVATE_CANARY commit")

    @contextmanager
    def transaction(*, write=False):
        nonlocal failed
        if failed:
            raise sqlite3.OperationalError("PRIVATE_CANARY recovery read")
        with original(write=write) as db:
            yield db
            if write:
                failed = True
                raise root

    monkeypatch.setattr(service.repository, "transaction", transaction)
    with pytest.raises(ProductError) as exc:
        service.upload(png(), "hoa_don", "synthetic", "test.png", "key")
    assert exc.value.__cause__ is root
    assert "retained" in caplog.text and "PRIVATE_CANARY" not in caplog.text
    assert len(list(service.storage.root.iterdir())) == 2
    monkeypatch.setattr(service.repository, "transaction", original)
    assert row_counts(service) == [0, 0, 0]


def test_failed_upload_retry_remains_owner_scoped(session_api, monkeypatch):
    api, _ = session_api
    state = login(api, "alpha")
    path = "/api/v1/documents?document_type=hoa_don&data_origin=synthetic"
    headers = {
        "Origin": ORIGIN,
        "X-CSRF-Token": state["csrf_token"],
        "Idempotency-Key": "shared-failure-key",
    }
    storage = api.app.state.documents.storage
    original = storage.write

    def fail(*_):
        raise OSError(errno.ENOSPC, "synthetic disk error")

    monkeypatch.setattr(storage, "write", fail)
    assert api.post(path, content=png(), headers=headers).status_code == 500
    monkeypatch.setattr(storage, "write", original)
    alpha = api.post(path, content=png(), headers=headers)
    assert alpha.status_code == 202
    state = login(api, "beta")
    headers["X-CSRF-Token"] = state["csrf_token"]
    assert api.get("/api/v1/documents").json()["total"] == 0
    assert api.get("/api/v1/documents/" + alpha.json()["document_id"]).status_code == 404
    beta = api.post(path, content=png(), headers=headers)
    assert beta.status_code == 202 and beta.json()["document_id"] != alpha.json()["document_id"]
    assert api.get("/api/v1/documents").json()["total"] == 1
