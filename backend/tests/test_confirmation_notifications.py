"""Real SQLite workflow with explicit notification doubles; no external delivery."""

import asyncio
import copy
import dataclasses
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest
from pydantic import ValidationError
from test_product import processed, revision_request
from test_product import product as product

from docintel.config import Settings
from docintel.services.notifications import DocumentConfirmed, notify_safely


class Sender:
    def __init__(self, service, mode="success"):
        self.service, self.mode = service, mode
        self.events = []
        self.cancelled = threading.Event()

    async def send(self, notice):
        # A separate writer can observe confirmed state: business transaction is committed.
        with self.service.repository.transaction(write=True) as connection:
            assert (
                connection.execute(
                    "SELECT review_status FROM revisions WHERE run_id=? AND revision=?",
                    (notice.run_id, notice.revision),
                ).fetchone()[0]
                == "confirmed"
            )
        self.events.append(notice)
        if self.mode == "error":
            raise RuntimeError("private-source-text must not be logged")
        if self.mode == "timeout":
            try:
                await asyncio.sleep(3600)
            finally:
                self.cancelled.set()


def test_caller_cancellation_propagates_without_detached_delivery():
    async def run():
        entered, cancelled = asyncio.Event(), asyncio.Event()

        class Blocked:
            async def send(self, notice):
                entered.set()
                try:
                    await asyncio.sleep(3600)
                finally:
                    cancelled.set()

        notice = DocumentConfirmed("a" * 32, "b" * 32, 1)
        task = asyncio.create_task(notify_safely(Blocked(), notice, 1.0))
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cancelled.is_set()

    asyncio.run(run())


@pytest.mark.parametrize(
    "options",
    [
        {"notification_mode": "email"},
        {"notification_timeout_seconds": 0},
        {"notification_timeout_seconds": 1.1},
        {"notification_timeout_seconds": float("inf")},
    ],
)
def test_invalid_delivery_configuration_is_rejected(options):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **options)


@pytest.mark.parametrize("mode", ["success", "error", "timeout"])
def test_delivery_runs_after_commit_and_preserves_exact_response(product, caplog, mode):
    api, settings = product
    settings.notification_timeout_seconds = 0.02
    sender = Sender(api.app.state.documents, mode)
    api.app.state.confirmation_notifier = sender
    document = processed(api)
    expected = copy.deepcopy(document)
    # Both the summary and nested revision already expose this transition in the API.
    expected["review_status"] = "confirmed"
    expected["review"]["review_status"] = "confirmed"
    path = f"/api/v1/documents/{document['document_id']}"
    with caplog.at_level(logging.INFO):
        response = api.post(path + "/confirm", json=revision_request(document))
    assert response.status_code == 200
    assert response.json() == expected == api.get(path).json()
    assert len(sender.events) == 1
    notice = sender.events[0]
    assert dataclasses.asdict(notice) == {
        "document_id": document["document_id"],
        "run_id": document["run"]["run_id"],
        "revision": 1,
        "name": "document.confirmed",
    }
    assert notice.event_id == f"document.confirmed:{notice.run_id}:1"
    with pytest.raises(dataclasses.FrozenInstanceError):
        notice.revision = 2
    assert "private-source-text" not in caplog.text
    assert "Công ty" not in caplog.text
    if mode == "timeout":
        assert sender.cancelled.is_set()
    assert (
        api.get(path + "/export", params={"run_id": notice.run_id, "revision": 1}).status_code
        == 200
    )


def test_failed_business_requests_never_send(product):
    api, _ = product
    sender = Sender(api.app.state.documents)
    api.app.state.confirmation_notifier = sender
    document = processed(api)
    path = f"/api/v1/documents/{document['document_id']}"
    assert (
        api.post(
            path + "/confirm", json={**revision_request(document), "expected_revision": 99}
        ).status_code
        == 409
    )
    assert (
        api.post("/api/v1/documents/missing/confirm", json=revision_request(document)).status_code
        == 404
    )
    assert (
        api.post(
            path + "/confirm", json={**revision_request(document), "approved": True}
        ).status_code
        == 422
    )
    saved = api.put(
        path + "/review",
        json={
            **revision_request(document),
            "fields": {"seller_name": {"is_reviewed": True, "reviewed_value": None}},
        },
    ).json()
    assert api.post(path + "/confirm", json=revision_request(saved)).status_code == 422
    assert sender.events == []


def test_retry_and_concurrent_confirmation_only_notify_transition(product):
    api, _ = product
    sender = Sender(api.app.state.documents)
    api.app.state.confirmation_notifier = sender
    document = processed(api)
    path = f"/api/v1/documents/{document['document_id']}/confirm"

    def confirm():
        return api.post(path, json=revision_request(document))

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: confirm(), range(2)))
    assert all(response.status_code == 200 for response in responses)
    assert confirm().status_code == 200
    assert len(sender.events) == 1
    history = api.get(f"/api/v1/documents/{document['document_id']}/history").json()
    assert sum(item["action"] == "confirmed" for item in history["events"]) == 1


def test_rollback_does_not_publish_confirmation(product, monkeypatch):
    api, _ = product
    service = api.app.state.documents
    sender = Sender(service)
    api.app.state.confirmation_notifier = sender
    document = processed(api)
    transaction = service.repository.transaction

    @contextmanager
    def fail_commit(*, write=False):
        with transaction(write=write) as connection:
            yield connection
            if write:
                raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(service.repository, "transaction", fail_commit)
    with pytest.raises(RuntimeError, match="simulated commit failure"):
        api.post(
            f"/api/v1/documents/{document['document_id']}/confirm", json=revision_request(document)
        )
    assert sender.events == []
    assert service.detail(document["document_id"]).review.review_status == "draft"
