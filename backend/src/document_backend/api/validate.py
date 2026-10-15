from fastapi import APIRouter

from document_backend.services.validation import validate_review
from document_contracts.models import APIErrorResponse, ValidationRequest, ValidationResponse

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.post("/validate", response_model=ValidationResponse,
             responses={422: {"model": APIErrorResponse}, 500: {"model": APIErrorResponse}})
def validate(body: ValidationRequest) -> ValidationResponse:
    return validate_review(body)
