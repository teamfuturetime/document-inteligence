import asyncio

import pytest
from starlette.requests import Request

from docintel.api.auth_body import bounded_auth_body
from docintel.services.documents import ProductError


def test_auth_body_rejects_oversize_declaration_before_receive():
    async def receive():
        raise AssertionError("Credentials body should not be consumed")

    request = Request({"type": "http", "headers": [(b"content-length", b"4097")]}, receive)
    with pytest.raises(ProductError) as rejected:
        asyncio.run(bounded_auth_body(request))
    assert rejected.value.status == 413


def test_auth_body_has_one_total_receive_deadline():
    async def receive():
        await asyncio.sleep(3600)

    request = Request({"type": "http", "headers": []}, receive)
    with pytest.raises(ProductError) as rejected:
        asyncio.run(bounded_auth_body(request, timeout=0.01))
    assert (rejected.value.status, rejected.value.code) == (408, "AUTH_BODY_TIMEOUT")


def test_chunked_credential_body_cannot_exceed_limit():
    async def receive():
        return {"type": "http.request", "body": b"x" * 4097, "more_body": False}

    request = Request({"type": "http", "headers": []}, receive)
    with pytest.raises(ProductError) as rejected:
        asyncio.run(bounded_auth_body(request))
    assert rejected.value.status == 413
