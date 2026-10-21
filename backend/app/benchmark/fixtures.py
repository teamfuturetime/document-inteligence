"""Read-only fixture inputs/responses; fixture source text is not measured OCR."""

import json
from pathlib import Path

from app.benchmark.contracts import (
    BenchmarkCase, BenchmarkDataset, BenchmarkIdentity, BenchmarkRequest, OCRContext, digest,
)
from app.providers.contracts import ProviderError
from app.schemas.extraction import DocumentInput, ProviderIdentity
from app.schemas.invoice import InvoiceValues


def load_dataset(manifest_path: Path, sources_path: Path, labels_path: Path | None = None) -> BenchmarkDataset:
    manifest_bytes = manifest_path.read_bytes()
    source_bytes = sources_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    sources = json.loads(source_bytes)
    label_bytes = None if labels_path is None else labels_path.read_bytes()
    labels = None if label_bytes is None else json.loads(label_bytes)
    cases = []
    ids = [item["id"] for item in manifest["images"]]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate dataset ID")
    if labels is not None and set(labels["labels"]) - set(ids):
        raise ValueError("Labels contain unknown IDs")
    for item in manifest["images"]:
        path = (manifest_path.parent / item["file"]).resolve()
        if not path.is_relative_to(manifest_path.parent.resolve()):
            raise ValueError("Image path must stay within the dataset directory")
        content = path.read_bytes()
        if digest(content) != item["sha256"]:
            raise ValueError("Image hash mismatch")
        # Deliberate projection: never pass expected_text/label objects or paths to provider.
        image = DocumentInput(document_id=item["id"], media_type=item["media_type"], content=content)
        source = sources["sources"].get(item["id"])
        context = None if source is None else OCRContext.model_validate(source)
        if context and (context.document_id != image.document_id or context.input_sha256 != digest(content)):
            raise ValueError("OCR context does not match the sample")
        if context and (context.width, context.height) != (item["width"], item["height"]):
            raise ValueError("OCR dimensions do not match the frozen manifest")
        truth = None if labels is None else labels["labels"].get(item["id"])
        cases.append(BenchmarkCase(image, context, item.get("source_locale"),
                                   None if truth is None else InvoiceValues.model_validate(truth)))
    return BenchmarkDataset(tuple(cases), manifest["version"], digest(manifest_bytes),
                            None if labels is None else labels["version"],
                            None if label_bytes is None else digest(label_bytes), digest(source_bytes))


class FixtureResponseProvider:
    def __init__(self, path: Path) -> None:
        data = path.read_bytes()
        source = json.loads(data)
        self.source_sha256 = digest(data)
        self._version = source["version"]
        self._responses = source["responses"]

    @property
    def identity(self) -> BenchmarkIdentity:
        return BenchmarkIdentity(provider=ProviderIdentity(
            name="offline-response-fixture", implementation_version="1.0.0",
            config_version=self._version, mode="fake"), model_id=None, model_revision=None)

    def respond(self, request: BenchmarkRequest) -> str:
        try:
            choices = self._responses[request.sample_id]
            response = choices.get(request.mode, choices.get("default"))
            if not isinstance(response, str):
                raise ValueError("Fixture response must be a string")
            return response
        except (KeyError, TypeError, ValueError):
            raise ProviderError("provider_failed") from None
