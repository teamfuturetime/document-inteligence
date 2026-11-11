"""Best-effort review events; async adapters must honor cancellation and never block."""

import asyncio
from dataclasses import dataclass
import logging
from typing import Literal, Protocol

logger = logging.getLogger(__name__)
SEND_TIMEOUT_SECONDS = 0.05


@dataclass(frozen=True)
class ReviewValidated:
    invoice_number: str
    name: Literal["review.validated"] = "review.validated"


class ReviewNotifier(Protocol):
    async def send(self, event: ReviewValidated) -> None: ...


class LoggingReviewNotifier:
    """Local event sink, not a durable queue or an email delivery provider."""

    async def send(self, event: ReviewValidated) -> None:
        logger.info("business_event=%s", event.name)


async def notify_safely(sender: ReviewNotifier, event: ReviewValidated) -> None:
    try:
        # Cooperative deadline also cancels the send; no detached tasks or retries.
        async with asyncio.timeout(SEND_TIMEOUT_SECONDS):
            await sender.send(event)
    except Exception:
        # CancelledError derives from BaseException: caller cancellation still propagates.
        # Neither raw exception details nor invoice data belong in application logs.
        logger.warning("notification_delivery_failed event=%s", event.name)
