import hashlib
import json
from pathlib import Path

from docintel.domain.models import FIELD_IDS, FixtureManifest, GoldAnnotation


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if Path(relative).is_absolute() or not candidate.is_relative_to(root.resolve()):
        raise ValueError("Manifest path ngoài repository")
    return candidate


def validate_manifest(root: Path, manifest: FixtureManifest) -> list[GoldAnnotation]:
    ids: set[str] = set()
    hashes: set[str] = set()
    parent_splits: dict[str, str] = {}
    content_signatures: dict[str, str] = {}
    annotations = []
    for sample in manifest.samples:
        if sample.sample_id in ids:
            raise ValueError("sample_id trùng")
        ids.add(sample.sample_id)
        if sample.dataset_version != manifest.dataset_version:
            raise ValueError("Dataset version không đồng nhất")
        previous_split = parent_splits.setdefault(sample.parent_document_id, sample.split)
        if previous_split != sample.split:
            raise ValueError("Parent document overlap giữa splits")
        image = safe_path(root, sample.input_path)
        annotation_path = safe_path(root, sample.annotation_path)
        if checksum(annotation_path) != sample.annotation_sha256:
            raise ValueError("Checksum gold annotation không khớp manifest")
        actual = checksum(image)
        if actual != sample.input_sha256:
            raise ValueError("Checksum ảnh không khớp manifest")
        if actual in hashes:
            raise ValueError("File ảnh trùng checksum")
        hashes.add(actual)
        annotation = GoldAnnotation.model_validate_json(annotation_path.read_text(encoding="utf-8"))
        if annotation.sample_id != sample.sample_id or set(annotation.fields) != set(FIELD_IDS):
            raise ValueError("Gold ID hoặc tập field không khớp schema")
        signature = json.dumps(
            annotation.model_dump()["fields"], ensure_ascii=False, sort_keys=True
        )
        if signature in content_signatures and content_signatures[signature] != sample.split:
            raise ValueError("Nội dung nhãn trùng giữa splits; cần kiểm tra leakage")
        content_signatures[signature] = sample.split
        annotations.append(annotation)
    return annotations
