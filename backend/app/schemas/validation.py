"""Structured validation results; no extraction or review confirmation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.invoice import InvoiceValues

FieldName = Literal[
    "invoice_number", "invoice_date", "seller_name", "total_amount", "currency"
]


class FieldIssue(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    field: FieldName | None
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ValidationResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    valid: bool
    normalized_values: InvoiceValues
    errors: list[FieldIssue]
    warnings: list[FieldIssue]

    @model_validator(mode="after")
    def consistent_result(self) -> "ValidationResult":
        complete = all(value is not None for value in self.normalized_values.model_dump().values())
        if self.valid != (complete and not self.errors):
            raise ValueError("valid must agree with completeness and errors")
        if not self.valid and not self.errors:
            raise ValueError("An invalid result must explain at least one error")
        return self
