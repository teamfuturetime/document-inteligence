"""Provider execution followed by the unchanged S2.2 normalization/validation."""

from dataclasses import replace
import hashlib
import json

from pydantic import ValidationError

from app.providers.contracts import ExtractionProvider, ProviderError
from app.schemas.extraction import (
    DocumentInput, PipelineError, PipelineFailure, PipelineSuccess, ProviderIdentity,
    ProviderOutput, RunMetadata,
)
from app.schemas.validation import FieldIssue
from app.services.normalization import NORMALIZATION_VERSION, normalize_invoice
from app.services.validation import validate_invoice

PIPELINE_VERSION = "extraction-pipeline-1"
_ERROR_MESSAGES = {
    "invalid_input": "Document input does not satisfy the pipeline contract",
    "invalid_provider_output": "Provider returned an invalid extraction contract",
    "provider_unavailable": "Extraction provider is unavailable",
    "provider_timeout": "Extraction provider timed out",
    "provider_failed": "Extraction provider failed",
    "invalid_document": "Provider could not process the document",
}


def run_pipeline(
    document: DocumentInput, provider: ExtractionProvider, *, code_revision: str | None = None
) -> PipelineSuccess | PipelineFailure:
    metadata = None
    document_id = None

    def failure(code: str) -> PipelineFailure:
        return PipelineFailure(document_id=document_id, run_metadata=metadata,
                               error=PipelineError(code=code, message=_ERROR_MESSAGES[code]))

    try:
        if not isinstance(document, DocumentInput):
            return failure("invalid_input")
        document = DocumentInput.model_validate(document.model_dump(warnings=False))
        document_id = document.document_id
    except (ValidationError, TypeError, ValueError):
        return failure("invalid_input")
    try:
        identity = provider.identity
        if not isinstance(identity, ProviderIdentity):
            return failure("invalid_provider_output")
        identity = ProviderIdentity.model_validate(identity.model_dump(warnings=False))
        digest = hashlib.sha256(document.content).hexdigest()
        signature = json.dumps({"document_id": document_id, "content": digest,
                                "media_type": document.media_type, "provider": identity.model_dump(),
                                "pipeline": PIPELINE_VERSION, "normalization": NORMALIZATION_VERSION,
                                "code_revision": code_revision}, sort_keys=True).encode()
        metadata = RunMetadata(
            run_id=hashlib.sha256(signature).hexdigest(), content_sha256=digest,
            provider=identity, pipeline_version=PIPELINE_VERSION,
            normalization_version=NORMALIZATION_VERSION, code_revision=code_revision,
        )
    except Exception:
        return failure("invalid_provider_output")
    try:
        output = provider.extract(document)
    except ProviderError as exc:
        code = exc.code if exc.code in {"provider_unavailable", "provider_timeout", "provider_failed", "invalid_document"} else "provider_failed"
        return failure(code)
    except TimeoutError:
        return failure("provider_timeout")
    except ValidationError:
        return failure("invalid_provider_output")
    except Exception:
        return failure("provider_failed")
    try:
        if not isinstance(output, ProviderOutput):
            return failure("invalid_provider_output")
        # Re-validate even pre-built/mutated/model_construct outputs at the boundary.
        output = ProviderOutput.model_validate(output.model_dump(warnings=False))
        if identity.mode == "fake" and (
            output.ocr_text is not None
            or not {"fake_data", "not_derived_from_document"}.issubset(output.warnings)
            or any(item.confidence is not None or item.evidence for item in output.field_metadata.values())
        ):
            return failure("invalid_provider_output")
    except (ValidationError, TypeError, ValueError):
        return failure("invalid_provider_output")

    normalized = normalize_invoice(output.raw_values, source_locale=output.source_locale)
    # Provider uncertainty blocks acceptance even if the text happens to parse.
    issues = list(normalized.errors)
    candidates = dict(normalized.candidates)
    for field in output.uncertain_fields:
        candidates[field] = None
        if not any(issue.field == field for issue in issues):
            issues.append(FieldIssue(field=field, code="extraction.uncertain_field",
                                     message="Provider could not select a reliable field value"))
    normalized = replace(normalized, candidates=candidates, errors=issues)
    return PipelineSuccess(
        document_id=document_id, run_metadata=metadata, provider_output=output,
        validation=validate_invoice(normalized),
    )
