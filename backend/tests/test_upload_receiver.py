import asyncio

import pytest
from starlette.requests import Request

from docintel.api.uploads import receive_upload
from docintel.config import Settings
from docintel.services.documents import ProductError


def test_oversize_declaration_never_requests_body():
    async def receive():
        raise AssertionError("oversize declaration must be rejected before receive")

    request = Request(
        {"type": "http", "http_version": "1.1", "headers": [(b"content-length", b"1025")]}, receive
    )
    with pytest.raises(ProductError) as error:
        asyncio.run(receive_upload(request, Settings(_env_file=None, max_upload_bytes=1024)))
    assert error.value.status == 413
    assert error.value.code == "FILE_TOO_LARGE"
