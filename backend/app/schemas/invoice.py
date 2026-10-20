"""Canonical values for sales_invoice 1.0.0; no raw-input normalization.

Extraction status, warnings, confidence and review confirmation belong to separate
envelopes. These models contain only the five required business value keys.
"""

from datetime import date
from typing import Annotated, Literal
import unicodedata

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

MAX_SAFE_INTEGER = 9_007_199_254_740_991


def _calendar_date(value: str) -> str:
    date.fromisoformat(value)
    return value


def _canonical_seller_name(value: str) -> str:
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError("Seller name must already be NFC-normalized")
    if " ".join(value.split()) != value:
        raise ValueError("Seller name must use single spaces without outer whitespace")
    if any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in value):
        raise ValueError("Seller name must not contain control or surrogate characters")
    if not any(char.isalpha() for char in value):
        raise ValueError("Seller name must contain at least one letter")
    return value


InvoiceNumber = Annotated[
    str,
    Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9./_-]{0,99}$"),
]
InvoiceDate = Annotated[
    str,
    Field(
        min_length=10,
        max_length=10,
        pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
        json_schema_extra={"format": "date"},
    ),
    AfterValidator(_calendar_date),
]
SellerName = Annotated[
    str, Field(min_length=1, max_length=200), AfterValidator(_canonical_seller_name)
]
Amount = Annotated[int, Field(ge=0, le=MAX_SAFE_INTEGER)]
Currency = Literal["VND"]


class _InvoiceContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)


class InvoiceValues(_InvoiceContract):
    """All five keys are required; null explicitly marks an unavailable value."""

    invoice_number: InvoiceNumber | None
    invoice_date: InvoiceDate | None
    seller_name: SellerName | None
    total_amount: Amount | None
    currency: Currency | None


class FinalInvoiceValues(_InvoiceContract):
    """Complete valid canonical values; user confirmation is a separate concern."""

    invoice_number: InvoiceNumber
    invoice_date: InvoiceDate
    seller_name: SellerName
    total_amount: Amount
    currency: Currency
