"""Exercise the health HTTP contract in-process with network access blocked."""

import socket
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    def reject_connection(*args, **kwargs):
        raise AssertionError("Health tests must not open network connections")

    # Windows asyncio creates a local socketpair when its event loop starts.
    # Block connections during requests, after that internal setup completes.
    with TestClient(app) as test_client:
        with monkeypatch.context() as guard:
            guard.setattr(socket.socket, "connect", reject_connection)
            guard.setattr(socket.socket, "connect_ex", reject_connection)
            guard.setattr(socket, "create_connection", reject_connection)
            yield test_client


def test_health_returns_ok_json(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}


def test_health_rejects_post(client: TestClient) -> None:
    response = client.post("/health")

    assert response.status_code == 405
    assert "GET" in response.headers["allow"]
