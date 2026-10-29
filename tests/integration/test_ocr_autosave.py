"""CT-01..03: concurrent HTTP requests, real auth/CSRF, persisted winner checks."""
import asyncio
from contextlib import AsyncExitStack
import json
from threading import Barrier

import httpx
import pytest

from app.models import Document
from app.repositories.documents import DocumentRepository
from scripts.ocr_autosave_support import (
    RAW_OCR, isolated_http_environment, login_owner, register_owner,
)


@pytest.fixture()
def http_environment(tmp_path):
    with isolated_http_environment(tmp_path) as environment:
        yield environment


def assert_persisted(environment, document_id, text):
    # A new Session after all workers have finished establishes durable state.
    with environment.sessions() as db:
        document = db.get(Document, document_id)
        assert document.ocr_revision == 1
        assert document.ocr_text_corrected == text
        assert document.ocr_text == RAW_OCR
        assert document.status == "reviewed"


async def race(environment, count):
    async with AsyncExitStack() as stack:
        clients = [await stack.enter_async_context(environment.client()) for _ in range(count)]
        owner_id = await register_owner(clients[0])
        for client in clients[1:]:
            await login_owner(client)
        # Sessions are independently issued by /login, rather than sharing a jar.
        assert len({tuple(client.cookies.items()) for client in clients}) == count
        document_id = environment.seed_documents(owner_id, 1)[0]
        gate = asyncio.Event()

        async def save(index):
            await gate.wait()
            text = f"Version {index}"
            response = await asyncio.wait_for(clients[index].patch(
                f"/api/v1/documents/{document_id}/ocr-correction",
                json={"text": text, "expected_revision": 0},
            ), timeout=25)
            return text, response

        tasks = [asyncio.create_task(save(index)) for index in range(count)]
        gate.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=30)
        winners = [(text, response) for text, response in results if response.status_code == 200]
        assert len(winners) == 1, [(text, response.status_code) for text, response in results]
        assert [response.status_code for _, response in results].count(409) == count - 1
        winner_text, response = winners[0]
        assert response.json()["ocr_revision"] == 1
        assert response.json()["ocr_text_cleaned"] == winner_text
        assert_persisted(environment, document_id, winner_text)
        reloaded = await clients[-1].get(f"/api/v1/documents/{document_id}")
        assert reloaded.status_code == 200
        assert reloaded.json()["ocr_text_cleaned"] == winner_text
        assert reloaded.json()["ocr_text_raw"] == RAW_OCR


@pytest.mark.parametrize("count", [2, 8], ids=["CT-01-two-requests", "CT-03-independent-sessions"])
def test_same_revision_has_exactly_one_persisted_http_winner(http_environment, monkeypatch, count):
    # Synchronize at the persistence boundary so every worker has passed auth
    # and CSRF before any conditional update can proceed.
    barrier = Barrier(count, timeout=15)
    original = DocumentRepository.save_ocr_correction

    def synchronized_update(self, *args, **kwargs):
        barrier.wait()
        return original(self, *args, **kwargs)

    monkeypatch.setattr(DocumentRepository, "save_ocr_correction", synchronized_update)
    asyncio.run(asyncio.wait_for(race(http_environment, count), timeout=45))


def test_CT_02_stale_request_arriving_later_cannot_overwrite(http_environment):
    async def scenario():
        async with http_environment.client() as client:
            owner_id = await register_owner(client)
            document_id = http_environment.seed_documents(owner_id, 1)[0]
            path = f"/api/v1/documents/{document_id}/ocr-correction"
            newer = await client.patch(path, json={"text": "New accepted draft", "expected_revision": 0})
            assert newer.status_code == 200
            stale = await client.patch(path, json={"text": "Old delayed draft", "expected_revision": 0})
            assert stale.status_code == 409
            assert "detail" in stale.json()
            reloaded = await client.get(f"/api/v1/documents/{document_id}")
            assert reloaded.status_code == 200
            assert reloaded.json()["ocr_revision"] == 1
            assert reloaded.json()["ocr_text_cleaned"] == "New accepted draft"
            assert_persisted(http_environment, document_id, "New accepted draft")

    asyncio.run(asyncio.wait_for(scenario(), timeout=30))


@pytest.mark.parametrize("corruption", ["invalid-json", "wrong-json-type", "wrong-acknowledgement", "unexpected-exception"])
def test_performance_harness_records_invalid_200_without_losing_report(http_environment, corruption):
    """A broken response must count as a failure even when the DB did save.

    Keep the real app, auth, CSRF and database writes, then corrupt one client
    response. This checks report generation as well as outcome classification.
    """
    from scripts.ocr_autosave_performance import measure_scenario

    class CorruptedClient:
        def __init__(self, client):
            self.client = client

        async def get(self, *args, **kwargs):
            return await self.client.get(*args, **kwargs)

        async def patch(self, *args, **kwargs):
            response = await self.client.patch(*args, **kwargs)
            assert response.status_code == 200
            if corruption == "unexpected-exception":
                raise RuntimeError("sensitive-response-marker")
            payload = {
                "invalid-json": b"sensitive-response-marker",
                "wrong-json-type": b"[]",
                "wrong-acknowledgement": b'{"ocr_revision":999,"ocr_text_cleaned":"sensitive-response-marker"}',
            }[corruption]
            return httpx.Response(200, content=payload, headers={"Content-Type": "application/json"})

    async def scenario():
        async with http_environment.client() as first, http_environment.client() as second:
            await register_owner(first)
            await login_owner(second)
            report = await measure_scenario(http_environment, [CorruptedClient(first), second], "corrupt-response", False)
            assert report["total_requests"] == 2
            assert report["successful_requests"] == 1
            assert report["failed_requests"] == 1
            assert report["outcome_distribution"] == {"unexpected_error": 1, "success": 1}
            assert report["correctness_passed"] is False
            assert report["database_invariant_passed"] is False
            assert report["requests"][0]["outcome"] == "unexpected_error"
            assert report["requests"][0]["error_type"]
            assert "sensitive-response-marker" not in json.dumps(report)
            assert all(row["revision"] == 1 and row["raw_unchanged"] for row in report["database_final_state"])

    asyncio.run(asyncio.wait_for(scenario(), timeout=30))
