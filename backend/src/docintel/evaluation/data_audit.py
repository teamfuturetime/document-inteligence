"""Read-only product label/provenance audit. Never imported by inference."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from document_pipeline.normalization import text_value

from docintel.domain.documents import DEFINITIONS
from docintel.evaluation.product import read_manifest, safe_file


def audit_product_manifest(root: Path, path: Path) -> dict:
    """Check all labels, then expose coverage and template leakage without scores."""
    manifest = read_manifest(root, path)
    if not manifest["samples"]:
        raise ValueError("Product audit requires samples")
    statuses = Counter()
    splits = Counter()
    document_splits = defaultdict(Counter)
    templates = defaultdict(Counter)
    quality_tags = Counter()
    parents = set()
    signatures = {}
    for sample in manifest["samples"]:
        sample_id = sample["sample_id"]
        annotation = json.loads(
            safe_file(root, sample["annotation_path"]).read_text(encoding="utf-8")
        )
        definitions = DEFINITIONS[sample["document_type"]]
        fields = annotation.get("fields")
        if annotation.get("sample_id") != sample_id:
            raise ValueError(f"{sample_id}: annotation sample_id mismatch")
        if not isinstance(fields, dict) or set(fields) != {d.field_id for d in definitions}:
            raise ValueError(f"{sample_id}: annotation fields mismatch")
        for definition in definitions:
            key = definition.field_id
            field = fields[key]
            if not isinstance(field, dict) or set(field) != {"status", "value"}:
                raise ValueError(f"{sample_id}/{key}: invalid label shape")
            status, value = field["status"], field["value"]
            if status not in ("present", "absent", "unreadable"):
                raise ValueError(f"{sample_id}/{key}: invalid label status")
            if status != "present":
                if value is not None:
                    raise ValueError(f"{sample_id}/{key}: absent/unreadable must be null")
            elif definition.value_type == "integer":
                if type(value) is not int:
                    raise ValueError(f"{sample_id}/{key}: expected integer label")
            elif not isinstance(value, str) or not value or text_value(value) != value:
                raise ValueError(f"{sample_id}/{key}: expected nonempty NFC/whitespace text")
            statuses[status] += 1
        # Ignore sample IDs in this signature: identical labels across splits need review.
        signature = json.dumps(
            [sample["document_type"], fields], ensure_ascii=False, sort_keys=True
        )
        split = sample["split"]
        previous = signatures.setdefault(signature, split)
        if previous != split:
            raise ValueError(f"{sample_id}: identical label content across splits")
        splits[split] += 1
        document_splits[sample["document_type"]][split] += 1
        templates[sample["template_id"]][split] += 1
        quality_tags.update(sample["quality_tags"])
        parents.add(sample["parent_document_id"])
    return {
        "audit_version": "1.0.0",
        "purpose": "dataset_integrity_audit; not OCR inference or human label approval",
        "dataset_version": manifest["dataset_version"],
        "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "provenance": manifest["provenance"],
        "samples": len(manifest["samples"]),
        "parents": len(parents),
        "splits": dict(sorted(splits.items())),
        "document_splits": {
            key: dict(sorted(value.items())) for key, value in sorted(document_splits.items())
        },
        "field_statuses": dict(sorted(statuses.items())),
        "quality_tags": dict(sorted(quality_tags.items())),
        "template_splits": {
            key: dict(sorted(value.items())) for key, value in sorted(templates.items())
        },
        "templates_shared_across_splits": sorted(
            key for key, value in templates.items() if len(value) > 1
        ),
        "new_inference": False,
        "visual_review_performed": False,
    }
