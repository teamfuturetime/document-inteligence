"""A structural protocol, with no provider registry, SDK or base implementation."""

from typing import Literal, Protocol, runtime_checkable

from app.schemas.extraction import DocumentInput, ProviderIdentity, ProviderOutput


class ProviderError(Exception):
    """Expected provider failure; public responses use a fixed message per code."""

    def __init__(self, code: Literal[
        "provider_unavailable", "provider_timeout", "provider_failed", "invalid_document"
    ]) -> None:
        self.code = code
        super().__init__(code)


@runtime_checkable
class ExtractionProvider(Protocol):
    @property
    def identity(self) -> ProviderIdentity: ...

    def extract(self, document: DocumentInput) -> ProviderOutput:
        """Return raw candidates or raise ProviderError; no normalization/review."""
        ...
