"""VT-046: test-first contract, partitions, failure isolation and bounded input."""

import asyncio
from dataclasses import FrozenInstanceError
import json
import logging

from fastapi.testclient import TestClient
import pytest

from document_backend.main import create_app
from document_backend.services.validation import validate_review
from document_contracts.models import ValidationRequest

LIMIT = 32 * 1024  # Independent requirement oracle, not imported from implementation.


def payload(**changes):
    return {"schema_version": "1.0.0", "values": {
        "invoice_number": "  VT046-17  ", "invoice_date": "2024-02-29",
        "seller_name": "Cửa hàng Mây Việt", "total_amount": "125.000", "currency": "vnđ",
        **changes,
    }}


class Sender:
    def __init__(self, outcome="ok"):
        self.events = []
        self.outcome = outcome
        self.cancelled = False

    async def send(self, event):
        self.events.append(event)
        if self.outcome == "error":
            raise OSError("private-provider-token")
        if self.outcome == "hang":
            try:
                await asyncio.Event().wait()
            finally:
                self.cancelled = True


def configured(sender):
    app = create_app()
    app.state.review_notifier = sender
    return app


@pytest.mark.parametrize("outcome", ["ok", "error", "hang"])
def test_valid_result_survives_delivery_outcome(outcome, caplog):
    """TC01/04/05: exact independent wire values also kill mapping mutants."""
    sender = Sender(outcome)
    with caplog.at_level(logging.WARNING), TestClient(configured(sender)) as client:
        response = client.post("/api/v1/validate", json=payload())
    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "1.0.0", "valid": True, "errors": [],
        "normalized_values": {"invoice_number": "VT046-17", "invoice_date": "2024-02-29",
                              "seller_name": "Cửa hàng Mây Việt", "total_amount": 125000,
                              "currency": "VND"},
    }
    assert len(sender.events) == 1
    event = sender.events[0]
    assert event.name == "review.validated"
    assert event.invoice_number == "VT046-17"
    assert set(vars(event)) == {"name", "invoice_number"}
    assert "private-provider-token" not in caplog.text
    assert "Cửa hàng" not in caplog.text
    if outcome == "hang":
        assert sender.cancelled  # No orphaned delivery after request finishes.
    if outcome != "ok":
        assert "notification_delivery_failed" in caplog.text


@pytest.mark.parametrize("changes", [
    {"invoice_number": None}, {"seller_name": " "},
    {"currency": "USD"}, {"total_amount": "9" * 1000},
])
def test_field_invalid_never_notifies(changes):
    """TC02: shape-valid but semantically invalid partitions, including largest field."""
    sender = Sender()
    body = payload(**changes)
    expected = validate_review(ValidationRequest.model_validate(body)).model_dump(mode="json")
    with TestClient(configured(sender)) as client:
        response = client.post("/api/v1/validate", json=body)
    assert response.status_code == 200
    assert response.json() == expected
    assert response.json()["valid"] is False
    assert sender.events == []


@pytest.mark.parametrize("body", [
    b"{broken", b"[]", json.dumps(payload(total_amount=125000)).encode(),
    json.dumps(payload(seller_name="x" * 1001)).encode(),
    json.dumps({**payload(), "extra": "private-input"}).encode(),
])
def test_bad_wire_never_notifies(body):
    """TC03/09: malformed/type/extra/overlong shape partitions."""
    sender = Sender()
    with TestClient(configured(sender)) as client:
        response = client.post("/api/v1/validate", content=body,
                               headers={"content-type": "application/json"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert "private-input" not in response.text
    assert sender.events == []


@pytest.mark.parametrize("size,status", [(LIMIT - 1, 200), (LIMIT, 200), (LIMIT + 1, 413)])
def test_body_boundary_before_json_parser(size, status):
    """TC06/07: valid JSON padded with legal whitespace isolates byte-limit reason."""
    raw = json.dumps(payload(), ensure_ascii=False).encode()
    raw += b" " * (size - len(raw))
    sender = Sender()
    with TestClient(configured(sender)) as client:
        response = client.post("/api/v1/validate", content=raw,
                               headers={"content-type": "application/json"})
    assert response.status_code == status
    assert len(sender.events) == (1 if status == 200 else 0)
    if status == 413:
        assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize("headers", [{}, {"content-length": "1"}])
def test_large_chunked_input_does_not_trust_content_length(headers):
    """TC08: actual bytes, including a non-JSON oversize input, must yield 413 first."""
    sender = Sender()
    def chunks():
        yield b"x" * (LIMIT // 2)
        yield b"x" * (LIMIT // 2 + 1)
    with TestClient(configured(sender)) as client:
        response = client.post("/api/v1/validate", content=chunks(),
                               headers={"content-type": "application/json", **headers})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "invalid_request"
    assert sender.events == []


def test_stream_stops_after_first_excess_chunk():
    """TC08: no consumption of later chunks after hitting the cap."""
    from document_backend.api.validate import bounded_validation_body
    from document_backend.errors import DocumentError
    consumed = []
    async def stream():
        for i in range(3):
            consumed.append(i)
            yield b"x" * LIMIT
    with pytest.raises(DocumentError) as caught:
        asyncio.run(bounded_validation_body(stream()))
    assert caught.value.status == 413
    assert consumed == [0, 1]


def test_receive_deadline_uses_contract_error(monkeypatch):
    """TC10: slow receive, shorter injected budget; no external network or clock mocking."""
    import document_backend.api.validate as module
    from document_backend.errors import DocumentError
    monkeypatch.setattr(module, "RECEIVE_TIMEOUT_SECONDS", 0.01)
    async def stream():
        await asyncio.Event().wait()
        yield b"never"
    with pytest.raises(DocumentError) as caught:
        asyncio.run(module.bounded_validation_body(stream()))
    assert caught.value.status == 504
    assert caught.value.code == "processing_timeout"


def test_delivery_has_deadline_and_event_is_immutable():
    """TC05/11: independent 0.5s watchdog detects a missing production deadline."""
    from document_backend.services.notifications import ReviewValidated, notify_safely
    event = ReviewValidated(invoice_number="VT046-17")
    with pytest.raises(FrozenInstanceError):
        event.invoice_number = "corrupted"
    sender = Sender("hang")
    asyncio.run(asyncio.wait_for(notify_safely(sender, event), timeout=0.5))
    assert sender.cancelled


def test_request_cancellation_propagates():
    """TC11: exception isolation must not swallow caller cancellation."""
    from document_backend.services.notifications import ReviewValidated, notify_safely
    class CancelledSender:
        async def send(self, event):
            raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(notify_safely(CancelledSender(), ReviewValidated(invoice_number="VT046-17")))


def test_default_adapter_logs_event_without_invoice_values(caplog):
    """TC12: runnable default sink, without raw input leakage."""
    with caplog.at_level(logging.INFO), TestClient(create_app()) as client:
        response = client.post("/api/v1/validate", json=payload())
    assert response.status_code == 200
    assert "review.validated" in caplog.text
    assert "VT046-17" not in caplog.text
    assert "Cửa hàng" not in caplog.text


def test_separate_app_senders_do_not_share_state():
    """TC13: dependency belongs to each app, not a module-global recording list."""
    one, two = Sender(), Sender()
    with TestClient(configured(one)) as client:
        client.post("/api/v1/validate", json=payload(invoice_number="ONE"))
    with TestClient(configured(two)) as client:
        client.post("/api/v1/validate", json=payload(invoice_number="TWO"))
    assert [e.invoice_number for e in one.events] == ["ONE"]
    assert [e.invoice_number for e in two.events] == ["TWO"]
