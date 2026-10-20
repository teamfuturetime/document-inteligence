"""Validate normalized candidates using existing canonical models and rules."""

from copy import deepcopy

from pydantic import ValidationError

from app.schemas.invoice import FinalInvoiceValues, InvoiceValues
from app.schemas.validation import FieldIssue, ValidationResult
from app.services.normalization import FIELD_NAMES, NormalizationResult


def _canonical_issue(field: str, error_type: str, value: object) -> FieldIssue:
    if value is None:
        code, message = "business.required", "A value is required"
    elif error_type in {"greater_than_equal", "less_than_equal"}:
        code, message = "business.out_of_range", "Amount is outside the supported range"
    elif field == "invoice_date" and error_type == "value_error":
        code, message = "business.invalid_date", "Date does not exist in the calendar"
    elif field == "currency" and error_type == "literal_error":
        code, message = "business.unsupported_currency", "Only VND is supported"
    elif field == "seller_name" and error_type == "value_error":
        code, message = "business.invalid_seller_name", "Seller name does not meet the canonical text rules"
    elif error_type in {"string_too_short", "string_too_long"}:
        code, message = "schema.invalid_length", "Text length violates the schema"
    elif error_type == "string_pattern_mismatch":
        code, message = "schema.invalid_format", "Text format violates the schema"
    else:
        code, message = "schema.invalid_type", "Value type violates the schema"
    return FieldIssue(field=field, code=code, message=message)


def validate_invoice(normalized: NormalizationResult) -> ValidationResult:
    """Return all field errors without changing source or normalized candidates.

    Normalization failures remain errors, never silently become successful nulls.
    No additional tax, total reconciliation or date-range rules are assumed.
    """
    errors = deepcopy(normalized.errors)
    values = deepcopy(normalized.candidates)
    failed = {error.field for error in errors if error.field is not None}
    invalid_input = any(error.code == "schema.invalid_input" for error in errors)
    try:
        FinalInvoiceValues.model_validate(values)
    except ValidationError as exc:
        for error in exc.errors(include_input=False, include_url=False, include_context=False):
            field = error["loc"][0]
            if field not in failed and not invalid_input:
                errors.append(_canonical_issue(field, error["type"], values.get(field)))
                failed.add(field)
    for field in FIELD_NAMES:
        if field in failed or invalid_input:
            values[field] = None
    canonical = InvoiceValues.model_validate(values)
    complete = all(value is not None for value in canonical.model_dump().values())
    return ValidationResult(
        valid=complete and not errors,
        normalized_values=canonical,
        errors=errors,
        warnings=[],
    )
