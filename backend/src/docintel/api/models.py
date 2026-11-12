from typing import Literal

from docintel.domain.models import Contract, FieldId


class Health(Contract):
    status: Literal["ok"] = "ok"
    app_version: str


class Capabilities(Contract):
    provider_mode: Literal["unconfigured", "fixture", "tesseract"]
    ocr_ready: bool = False
    max_upload_bytes: int = 5_242_880
    model_benchmark_status: Literal["not_measured"] = "not_measured"
    supported_schemas: list[str]
    features: dict[str, Literal["implemented", "fixture", "planned", "unavailable"]]


class SchemaInfo(Contract):
    document_type: str
    schema_version: str
    status: Literal["provisional"] = "provisional"
    required_fields: list[FieldId]


class FixtureCatalog(Contract):
    prediction_source: Literal["fixture"] = "fixture"
    sample_ids: list[str]


class APIError(Contract):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(Contract):
    error: APIError
