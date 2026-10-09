"""Compatibility import for Phase 1; canonical models live in document_contracts."""

from document_contracts.models import (
    SCHEMA_VERSION, MAX_SAFE_INTEGER, FieldName, InvoiceNumber, SellerName,
    ISODate, Amount, Confidence, Version, Contract, InvoiceValues, FinalInvoiceValues,
    BoundingBox, Evidence, ExtractedField, ExtractedFields, ExtractionResponse,
    ReviewedValues, ValidationRequest, FieldError, ValidationResponse, APIErrorDetail,
    APIErrorResponse, HealthResponse, OCRToken, OCRPage, OCRResult, ReviewedExport,
    CONTRACT_MODELS, calendar_date,
)
