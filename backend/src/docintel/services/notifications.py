"""Best-effort persisted confirmation delivery; see ADR0009 and VT-046@31a18bb."""

import logging
from dataclasses import dataclass
from typing import Literal, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentConfirmed:
    document_id: str
    run_id: str
    revision: int
    name: Literal["document.confirmed"] = "document.confirmed"

    @property
    def event_id(self) -> str:
        return f"{self.name}:{self.run_id}:{self.revision}"


class ConfirmationNotifier(Protocol):
    async def send(self, notice: DocumentConfirmed) -> None: ...


class LoggingConfirmationNotifier:
    """Recipient is the local operator; enable INFO and a handler to observe events."""

    async def send(self, notice: DocumentConfirmed) -> None:
        logger.info("business_event=%s", notice.name)
