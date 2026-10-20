"""Fixed synthetic fixtures. This adapter never reads/recognizes document pixels."""

from typing import Literal

from app.providers.contracts import ProviderError
from app.schemas.extraction import DocumentInput, FieldMetadata, ProviderIdentity, ProviderOutput
from app.schemas.invoice import InvoiceValues
from app.schemas.validation import FieldName


class FakeExtractionProvider:
    def __init__(self, scenario: Literal["complete", "partial", "failure", "timeout"] = "complete") -> None:
        if scenario not in {"complete", "partial", "failure", "timeout"}:
            raise ValueError("Unknown fake fixture scenario")
        self._scenario = scenario

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            name="fake-invoice-fixture", implementation_version="1.0.0",
            config_version=f"synthetic-{self._scenario}-1", mode="fake",
        )

    def extract(self, document: DocumentInput) -> ProviderOutput:
        if self._scenario == "failure":
            raise ProviderError("provider_failed")
        if self._scenario == "timeout":
            raise ProviderError("provider_timeout")
        raw_values: dict[FieldName, str | int | None] = {
            "invoice_number": "FAKE-0000123", "invoice_date": "03/04/2026",
            "seller_name": "DỮ LIỆU GIẢ — Cửa hàng AI-02", "total_amount": "125.000",
            "currency": "VND",
        }
        uncertain_fields: list[FieldName] = []
        if self._scenario == "partial":
            raw_values["seller_name"] = None
            raw_values["total_amount"] = "125,000"
            uncertain_fields = ["total_amount"]
        return ProviderOutput(
            raw_values=raw_values, source_locale="vi-VN", uncertain_fields=uncertain_fields,
            field_metadata={field: FieldMetadata(confidence=None, evidence=[]) for field in InvoiceValues.model_fields},
            ocr_text=None, warnings=["fake_data", "not_derived_from_document"],
        )
