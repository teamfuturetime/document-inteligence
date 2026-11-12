import hashlib
import time
from pathlib import Path

from document_pipeline import __version__
from document_pipeline.config import PipelineConfig
from document_pipeline.errors import PipelineError
from document_pipeline.extraction import CONFIDENCE_VERSION, RULES, RULES_SHA256, extract
from document_pipeline.models import DocumentType, InferenceResult
from document_pipeline.preprocessing import prepare_image
from document_pipeline.provenance import runtime_metadata
from document_pipeline.tesseract import recognize


class DocumentPipeline:
    def __init__(
        self,
        tessdata_dir: Path,
        executable: str = "tesseract",
        config: PipelineConfig | None = None,
    ):
        self.tessdata_dir = tessdata_dir
        self.executable = executable
        self.config = config or PipelineConfig()

    def run(self, data: bytes, document_type: DocumentType) -> InferenceResult:
        if document_type not in ("hoa_don", "don_de_nghi"):
            raise PipelineError("UNSUPPORTED_SCHEMA", "Loại tài liệu chưa được hỗ trợ.")
        started = time.monotonic()
        provenance = runtime_metadata()
        remaining = self.config.timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise PipelineError("PROCESSING_TIMEOUT", "Pipeline quá thời gian.")
        page = prepare_image(data, self.config.model_copy(update={"timeout_seconds": remaining}))
        remaining = self.config.timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise PipelineError("PROCESSING_TIMEOUT", "Pipeline quá thời gian.")
        tokens, engine = recognize(
            page,
            self.tessdata_dir,
            self.executable,
            self.config.model_copy(update={"timeout_seconds": remaining}),
        )
        predictions = extract(
            tokens, document_type, minimum_ocr_score=self.config.minimum_field_ocr_score
        )
        if time.monotonic() - started > self.config.timeout_seconds:
            raise PipelineError("PROCESSING_TIMEOUT", "Pipeline quá thời gian.")
        return InferenceResult(
            pipeline_version=__version__,
            document_type=document_type,
            image_width=page.width,
            image_height=page.height,
            tokens=tokens,
            fields=predictions,
            warnings=() if tokens else ("NO_TEXT_DETECTED",),
            metadata={
                **engine,
                **provenance,
                "input_sha256": hashlib.sha256(data).hexdigest(),
                "config": self.config.model_dump(),
                "config_sha256": self.config.sha256,
                "rules_version": RULES["version"],
                "rules_sha256": RULES_SHA256,
                "confidence_version": CONFIDENCE_VERSION,
                "preprocessing": page.metadata,
                "elapsed_seconds": round(time.monotonic() - started, 4),
                "prediction_source": "model",
                "report_type": "inference_run",
            },
        )
