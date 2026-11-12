"""Real SQLite workflow with explicit notification doubles; no external delivery."""

import asyncio

import pytest
from pydantic import ValidationError
from test_product import product as product

from docintel.config import Settings
from docintel.services.notifications import DocumentConfirmed, notify_safely


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


@pytest.mark.parametrize("options", [{"notification_mode": "email"}])
def test_invalid_delivery_configuration_is_rejected(options):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **options)
