"""Homework-only HTTP consumer of R05 services, NOT a production validation API."""

from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse

from app.schemas.validation import ValidationResult
from app.services.invoice_policy import InvoicePolicyError
from app.services.normalization import normalize_invoice
from app.services.validation import validate_invoice


def create_app(policy_path: Path) -> FastAPI:
    app = FastAPI(title="VT-045 local validation harness", docs_url=None, redoc_url=None)

    @app.get("/ready")
    def ready():
        return {"status": "ready", "scope": "synthetic-validation-harness"}

    @app.post("/validate", response_model=ValidationResult)
    def validate(raw: Any = Body(...)):
        try:
            return validate_invoice(normalize_invoice(raw, source_locale="vi-VN"), policy_path=policy_path)
        except InvoicePolicyError:
            return JSONResponse(status_code=503, content={
                "error": {"code": "invoice_policy_unavailable", "message": "Invoice policy is unavailable or invalid"}
            })

    return app


if __name__ == "__main__":
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    uvicorn.run(create_app(args.policy), host="127.0.0.1", port=args.port, log_level="warning", access_log=False)
