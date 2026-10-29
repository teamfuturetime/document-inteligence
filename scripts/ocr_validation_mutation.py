"""Reproduce VT-043's temporary blank-OCR validation mutation; always restore source.

Run from the repository root: python scripts/ocr_validation_mutation.py
Do not run other backend checks while this experiment edits the schema.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "backend/app/schemas/documents.py"
EVIDENCE = ROOT / "evidence/bt3-vt043"
TEST = "tests/integration/test_document_review.py::test_ocr_correction_rejects_whitespace"


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    original = SCHEMA.read_bytes()
    needle = b"if not value.strip():"
    if original.count(needle) != 1:
        raise RuntimeError("Expected exactly one blank-OCR validator; inspect source before mutation")
    mutated = original.replace(needle, b"if False:  # VT-043 temporary validation mutation")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / ".test-tools"), str(ROOT / "backend"), environment.get("PYTHONPATH", "")]
    )
    # Avoid stale timestamp-based bytecode when the schema is restored rapidly.
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    def run(name: str) -> int:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "pytest", TEST, "-q", "--tb=short", "-p", "no:cacheprovider"],
            cwd=ROOT, env=environment, capture_output=True, timeout=90,
        )
        (EVIDENCE / name).write_bytes(result.stdout + result.stderr)
        return result.returncode

    results: dict = {"test": TEST, "started_at_utc": datetime.now(timezone.utc).isoformat()}
    results["baseline_exit"] = run("mutation_before.log")
    if results["baseline_exit"] != 0:
        raise RuntimeError("Baseline failed; no mutation applied. See mutation_before.log")
    diff = "".join(difflib.unified_diff(
        original.decode("utf-8").replace("\r\n", "\n").splitlines(keepends=True),
        mutated.decode("utf-8").replace("\r\n", "\n").splitlines(keepends=True),
        fromfile="a/backend/app/schemas/documents.py", tofile="b/backend/app/schemas/documents.py",
        n=0,
    ))
    (EVIDENCE / "mutation.diff").write_text(diff, encoding="utf-8", newline="\n")
    try:
        SCHEMA.write_bytes(mutated)
        results["mutation_exit"] = run("mutation_fail.log")
    finally:
        SCHEMA.write_bytes(original)
        results["source_restored_byte_for_byte"] = SCHEMA.read_bytes() == original
        results["restored_sha256"] = hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
        results["restored_exit"] = run("mutation_restored.log")
        results["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        results["killed"] = results.get("mutation_exit") == 1
        (EVIDENCE / "mutation_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0 if results["killed"] and results["restored_exit"] == 0 and results["source_restored_byte_for_byte"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
