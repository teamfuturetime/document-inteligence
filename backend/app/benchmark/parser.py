"""Strict JSON parsing and grounded source lookup; never repairs model values."""

from dataclasses import dataclass, replace
import json
import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.benchmark.contracts import BenchmarkRequest
from app.schemas.extraction import Evidence, FieldMetadata, ProviderOutput
from app.schemas.validation import FieldIssue, FieldName, ValidationResult
from app.services.normalization import FIELD_NAMES, normalize_invoice
from app.services.validation import validate_invoice

PARSER_VERSION = "invoice-benchmark-parser-1"


class ResponseEnvelope(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    raw_values: dict[FieldName, str | int | None]
    evidence: dict[FieldName, list[str]] = Field(default_factory=dict)
    uncertain_fields: list[FieldName] = Field(default_factory=list)
    model_reported_scores: dict[FieldName, Annotated[float, Field(allow_inf_nan=False)] | None] = Field(default_factory=dict)


@dataclass(frozen=True)
class AdaptedResponse:
    status: str
    output: ProviderOutput | None
    candidate_validation: ValidationResult | None
    accepted_validation: ValidationResult | None
    issues: tuple[FieldIssue, ...]
    model_reported_scores: dict[str, float | None]


def _issue(field: FieldName | None, code: str) -> FieldIssue:
    return FieldIssue(field=field, code=code, message=code.replace(".", ": "))


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Non-finite JSON numbers are not allowed")


def adapt_response(raw: str, request: BenchmarkRequest) -> AdaptedResponse:
    def failed(status, issues):
        return AdaptedResponse(status, None, None, None, tuple(issues), {})

    if not isinstance(raw, str) or len(raw) > 1_000_000:
        return failed("parse_error", [_issue(None, "parse.invalid_response")])
    try:
        raw.encode("utf-8")
    except UnicodeError:
        return failed("parse_error", [_issue(None, "parse.invalid_unicode")])
    text = raw.strip()
    if text.startswith("```"):
        fence = re.fullmatch(r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n```", text, re.I | re.S)
        if fence is None:
            return failed("parse_error", [_issue(None, "parse.invalid_fence")])
        text = fence.group(1)
    try:
        data = json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject_constant)
        # Reject escaped lone surrogates and overflow-to-Infinity as well.
        json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError):
        return failed("parse_error", [_issue(None, "parse.invalid_json")])
    try:
        envelope = ResponseEnvelope.model_validate(data)
        missing = [field for field in FIELD_NAMES if field not in envelope.raw_values]
        if missing:
            return failed("schema_error", [_issue(field, "schema.missing_key") for field in missing])
        wrong_types = [field for field, value in envelope.raw_values.items()
                       if field != "total_amount" and value is not None and not isinstance(value, str)]
        if wrong_types:
            return failed("schema_error", [_issue(field, "schema.invalid_type") for field in wrong_types])
        metadata = {field: FieldMetadata(confidence=None, evidence=[]) for field in FIELD_NAMES}
        output = ProviderOutput(
            raw_values=envelope.raw_values, source_locale=request.source_locale,
            uncertain_fields=envelope.uncertain_fields, field_metadata=metadata,
            ocr_text=None if request.ocr is None else request.ocr.text, warnings=[],
        )
    except ValidationError as exc:
        issues = []
        for error in exc.errors(include_input=False, include_context=False, include_url=False):
            field = next((part for part in error["loc"] if part in FIELD_NAMES), None)
            issues.append(_issue(field, "schema." + error["type"]))
        return failed("schema_error", issues)

    normalized = normalize_invoice(output.raw_values, source_locale=request.source_locale)
    candidate = validate_invoice(normalized)
    source = {} if request.ocr is None else {span.id: span for span in request.ocr.spans}
    issues = []
    uncertain = set(output.uncertain_fields)
    for field in FIELD_NAMES:
        ids = envelope.evidence.get(field, [])
        value = output.raw_values[field]
        code = None
        if len(ids) != len(set(ids)):
            code = "evidence.duplicate_id"
        elif ids and any(item not in source for item in ids):
            code = "evidence.unknown_id"
        elif ids and value is None:
            code = "evidence.null_value_claim"
        elif (value is not None or candidate.normalized_values.model_dump()[field] is not None) and not ids:
            code = "evidence.missing"
        if code:
            issues.append(_issue(field, code))
            uncertain.add(field)
            continue
        if not ids:
            continue
        spans = [source[item] for item in ids]
        if spans != sorted(spans, key=lambda span: span.start) or any(
            right.start < left.end or request.ocr.text[left.end:right.start].strip()
            for left, right in zip(spans, spans[1:])
        ):
            issues.append(_issue(field, "evidence.noncontiguous"))
            uncertain.add(field)
            continue
        quote = request.ocr.text[spans[0].start:spans[-1].end]
        # A real source span is insufficient if it supports a different field value.
        compared = dict(output.raw_values)
        compared[field] = quote
        supported = validate_invoice(normalize_invoice(compared, source_locale=request.source_locale))
        equivalent = (isinstance(value, str) and quote == value) or (
            candidate.normalized_values.model_dump()[field] is not None
            and supported.normalized_values.model_dump()[field] == candidate.normalized_values.model_dump()[field]
        )
        if not equivalent:
            issues.append(_issue(field, "evidence.value_mismatch"))
            uncertain.add(field)
            continue
        output.field_metadata[field] = FieldMetadata(confidence=None, evidence=[
            Evidence(id=span.id, text=request.ocr.text[span.start:span.end], page=span.page,
                     bbox=None if span.bbox is None else span.bbox.model_copy(deep=True))
            for span in spans
        ])
    output.uncertain_fields = [field for field in FIELD_NAMES if field in uncertain]
    candidates = dict(normalized.candidates)
    errors = list(normalized.errors)
    for field in output.uncertain_fields:
        candidates[field] = None
        if not any(error.field == field for error in errors):
            errors.append(next((issue for issue in issues if issue.field == field),
                               _issue(field, "extraction.uncertain_field")))
    accepted = validate_invoice(replace(normalized, candidates=candidates, errors=errors))
    # Do not attach model-reported scores to FieldMetadata.confidence.
    return AdaptedResponse("processed", output, candidate, accepted, tuple(issues), dict(envelope.model_reported_scores))
