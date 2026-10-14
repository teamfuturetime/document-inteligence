"""Fixed demo output. Values are deliberately independent of uploaded content."""

from uuid import uuid4

from document_contracts.models import ExtractionResponse


def mock_extraction() -> ExtractionResponse:
    values = {
        "invoice_number": "SYN-0001", "invoice_date": "2026-10-09",
        "seller_name": "Cửa hàng Mây Việt - dữ liệu giả", "total_amount": 125000,
        "currency": "VND",
    }
    return ExtractionResponse.model_validate({
        "schema_version": "1.0.0", "document_id": str(uuid4()), "mode": "mock",
        "pipeline_version": "mock-demo-1", "ocr_version": "mock-not-run",
        "config_version": "mock-fixed-invoice-1",
        "fields": {key: {"value": value, "confidence": None, "evidence": [],
                         "warnings": ["mock_data"]} for key, value in values.items()},
        "warnings": ["mock_data", "not_derived_from_upload"],
    })
