"""One immutable policy snapshot per validation; never recover with defaults."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas.invoice import MAX_SAFE_INTEGER

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "invoice-policy.json"


class InvoicePolicyError(RuntimeError):
    """Policy could not be read or validated; caller must fail closed."""


class InvoicePolicy(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    policy_version: Literal["invoice-policy-1"]
    max_total_amount: int = Field(ge=0, le=MAX_SAFE_INTEGER)


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate policy key")
        result[key] = value
    return result


def load_invoice_policy(path: Path = DEFAULT_POLICY_PATH) -> InvoicePolicy:
    """Read current JSON without cache; publish edits by atomic replacement."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)
        return InvoicePolicy.model_validate(data)
    except (OSError, ValueError, ValidationError) as exc:
        raise InvoicePolicyError("Invoice policy is unavailable or invalid") from exc
