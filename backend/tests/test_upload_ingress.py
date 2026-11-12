"""Exercise ASGI body events, including cases normal HTTP clients cannot encode."""

import asyncio
import io
import json
import threading

import pytest
from PIL import Image

from docintel.api.app import create_app
from docintel.config import Settings
from docintel.services.documents import DocumentService


def png():
    output = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(output, format="PNG")
    return output.getvalue()


def app_for(tmp_path, monkeypatch, **options):
    monkeypatch.setattr(DocumentService, "ensure_ready", lambda self: {})
    return create_app(
        Settings(_env_file=None, runtime_dir=tmp_path, max_upload_bytes=1024, **options),
        start_worker=False,
    )


async def post(app, messages, headers=(), *, entered=None, pause=0):
    sent, index = [], 0
    finished = asyncio.Event()

    async def receive():
        nonlocal index
        if index < len(messages):
            if entered:
                entered.set()
            if pause:
                await asyncio.sleep(pause)
            message = messages[index]
            index += 1
            return message
        await finished.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)
        if message["type"] == "http.response.body" and not message.get("more_body", False):
            finished.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/documents",
        "raw_path": b"/api/v1/documents",
        "query_string": b"document_type=hoa_don&data_origin=synthetic",
        "root_path": "",
        "headers": [(b"host", b"localhost"), *headers],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
    }
    await app(scope, receive, send)
    start = next(message for message in sent if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"") for message in sent if message["type"] == "http.response.body"
    )
    return start["status"], json.loads(body), dict(start["headers"]), index


def body(data, more=False):
    return {"type": "http.request", "body": data, "more_body": more}


def assert_empty(app):
    service = app.state.documents
    with service.repository.transaction() as connection:
        for table in ("documents", "runs", "events"):
            assert connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    assert list(service.storage.root.iterdir()) == []
    assert app.state.upload_limiter.borrowed_tokens == 0


@pytest.mark.parametrize(
    ("headers", "messages", "status", "code"),
    [
        ([(b"content-length", b"1025")], [], 413, "FILE_TOO_LARGE"),
        ([(b"content-length", b"-1")], [], 400, "INVALID_CONTENT_LENGTH"),
        ([(b"content-length", b"bad")], [], 400, "INVALID_CONTENT_LENGTH"),
        ([(b"content-length", b"9" * 5000)], [], 400, "INVALID_CONTENT_LENGTH"),
        (
            [(b"content-length", b"1"), (b"content-length", b"1")],
            [],
            400,
            "INVALID_CONTENT_LENGTH",
        ),
        (
            [(b"content-length", b"10"), (b"transfer-encoding", b"chunked")],
            [],
            400,
            "INVALID_CONTENT_LENGTH",
        ),
        ([], [body(b"x" * 1025)], 413, "FILE_TOO_LARGE"),
        ([], [body(b"x" * 700, True), body(b"x" * 325)], 413, "FILE_TOO_LARGE"),
        ([(b"content-length", b"1")], [body(png())], 400, "UPLOAD_LENGTH_MISMATCH"),
        ([(b"content-length", b"1000")], [body(png())], 400, "UPLOAD_LENGTH_MISMATCH"),
        ([], [body(b"partial", True), {"type": "http.disconnect"}], 400, "UPLOAD_DISCONNECTED"),
    ],
)
def test_rejects_before_persistence(tmp_path, monkeypatch, headers, messages, status, code):
    app = app_for(tmp_path, monkeypatch)

    async def run():
        async with app.router.lifespan_context(app):
            result, payload, response_headers, consumed = await asyncio.wait_for(
                post(app, messages, headers), 2
            )
            assert result == status
            assert payload["error"]["code"] == code
            assert payload["error"]["request_id"] == response_headers[b"x-request-id"].decode()
            assert response_headers[b"connection"] == b"close"
            if not messages:
                assert consumed == 0
            assert_empty(app)
            # Rejection must free the slot for the next complete upload.
            assert (await post(app, [body(png())]))[0] == 202

    asyncio.run(run())


def test_admission_has_no_wait_queue_and_cancel_releases_slot(tmp_path, monkeypatch):
    app = app_for(tmp_path, monkeypatch, max_concurrent_uploads=1)

    async def run():
        async with app.router.lifespan_context(app):
            entered = asyncio.Event()
            slow = asyncio.create_task(post(app, [body(b"x", True)], entered=entered, pause=60))
            await asyncio.wait_for(entered.wait(), 2)
            assert app.state.upload_limiter.borrowed_tokens == 1
            status, payload, _, consumed = await post(app, [])
            assert status == 429
            assert payload["error"]["code"] == "UPLOAD_BUSY"
            assert consumed == 0
            slow.cancel()
            with pytest.raises(asyncio.CancelledError):
                await slow
            assert_empty(app)
            assert (await post(app, [body(png())]))[0] == 202

    asyncio.run(run())


def test_cancellation_during_persistence_keeps_slot_until_worker_finishes(tmp_path, monkeypatch):
    app = app_for(tmp_path, monkeypatch, max_concurrent_uploads=1)
    started, finish = threading.Event(), threading.Event()

    async def run():
        async with app.router.lifespan_context(app):
            service = app.state.documents
            original = service.upload

            def blocked(*args):
                started.set()
                assert finish.wait(5)
                return original(*args)

            monkeypatch.setattr(service, "upload", blocked)
            request = asyncio.create_task(post(app, [body(png())]))
            try:
                assert await asyncio.to_thread(started.wait, 2)
                request.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await request
                assert app.state.upload_limiter.borrowed_tokens == 1
                assert (await post(app, []))[0] == 429
            finally:
                finish.set()
                await asyncio.gather(*app.state.upload_tasks)
            assert app.state.upload_limiter.borrowed_tokens == 0
            # A fully received body may commit despite a lost response. Its key allows retry.
            assert service.list_documents(20, 0).total == 1

    asyncio.run(run())


def test_shutdown_waits_for_inflight_upload(tmp_path, monkeypatch):
    app = app_for(tmp_path, monkeypatch)

    async def run():
        context = app.router.lifespan_context(app)
        await context.__aenter__()
        release = asyncio.Event()
        task = asyncio.create_task(release.wait())
        app.state.upload_tasks.add(task)
        task.add_done_callback(app.state.upload_tasks.discard)
        shutdown = asyncio.create_task(context.__aexit__(None, None, None))
        try:
            await asyncio.sleep(0)
            assert not shutdown.done()
        finally:
            release.set()
            await asyncio.wait_for(shutdown, 2)
        assert task.done()

    asyncio.run(run())


@pytest.mark.parametrize("headers", [[], [(b"content-length", str(len(png())).encode())]])
def test_complete_upload_and_idempotent_retry_with_full_queue(tmp_path, monkeypatch, headers):
    app = app_for(tmp_path, monkeypatch, max_pending_runs=1)

    async def run():
        async with app.router.lifespan_context(app):
            key = (b"idempotency-key", b"ingress-retry")
            data = png()
            messages = [body(data[:20], True), body(data[20:])]
            first = await post(app, messages, [*headers, key])
            retry = await post(app, messages, [*headers, key])
            assert first[0] == retry[0] == 202
            assert first[1]["document_id"] == retry[1]["document_id"]
            conflict = await post(app, [body(b"different")], [key])
            assert conflict[0] == 409
            assert conflict[1]["error"]["code"] == "IDEMPOTENCY_CONFLICT"
            service = app.state.documents
            with service.repository.transaction() as connection:
                for table in ("documents", "runs", "events"):
                    assert connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 1
            assert len(list(service.storage.root.iterdir())) == 2
            assert app.state.upload_limiter.borrowed_tokens == 0

    asyncio.run(run())


@pytest.mark.parametrize("messages", [[], [body(b"x", True)] * 20])
def test_total_receive_deadline_includes_trickled_chunks(tmp_path, monkeypatch, messages):
    app = app_for(tmp_path, monkeypatch, upload_receive_timeout_seconds=0.12)

    async def run():
        async with app.router.lifespan_context(app):
            result = await post(app, messages, pause=0.025)
            assert result[0] == 408
            assert result[1]["error"]["code"] == "UPLOAD_TIMEOUT"
            assert result[3] < 20
            assert_empty(app)
            assert (await post(app, [body(png())]))[0] == 202

    asyncio.run(run())


def test_exact_byte_cap_is_accepted(tmp_path, monkeypatch):
    app = app_for(tmp_path, monkeypatch)

    async def run():
        async with app.router.lifespan_context(app):
            data = png()
            padded = data + b"\0" * (1024 - len(data))
            result = await post(app, [body(padded)], [(b"content-length", b"1024")])
            assert result[0] == 202

    asyncio.run(run())
