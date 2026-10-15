import hashlib
import json
from pathlib import Path

from document_contracts.models import InvoiceValues


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_dataset(manifest: Path, split: str):
    root = manifest.parent.resolve()
    raw = manifest.read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError("Manifest exceeds limit")
    spec = json.loads(raw)
    if spec["schema_version"] != "1.0.0":
        raise ValueError("Unsupported schema")
    rows, identifiers = [], set()
    for item in spec["documents"]:
        if item["id"] in identifiers or item["split"] not in {"dev", "test"}:
            raise ValueError("Duplicate ID or invalid split")
        identifiers.add(item["id"])
        files = {}
        for key, hash_key, limit in [("file", "sha256", 10 * 1024 * 1024),
                                     ("ground_truth", "ground_truth_sha256", 64 * 1024)]:
            path = (root / item[key]).resolve()
            if not path.is_relative_to(root) or path.stat().st_size > limit:
                raise ValueError("Dataset path escapes root or exceeds limit")
            files[key] = path.read_bytes()
            if digest(files[key]) != item[hash_key]:
                raise ValueError(f"Dataset hash mismatch: {item['id']}")
        truth = InvoiceValues.model_validate_json(files["ground_truth"])
        if split == "all" or item["split"] == split:
            rows.append((item, files["file"], truth))
    return spec, digest(raw), rows
