"""Reproduce VT-042 mutation, coverage and order/repeat experiments."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST = "backend/tests/test_async_retry_vt042.py"


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run(output, name, arguments):
    result = subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    (output / name).write_text(
        result.stdout + result.stderr, encoding="utf-8", newline="\n"
    )
    print(name, "exit", result.returncode, flush=True)
    return result


def mutation(output):
    target = ROOT / "backend/src/docintel/api/documents.py"
    original = target.read_bytes()
    needle = b"len(data) + len(chunk) > maximum"
    assert original.count(needle) == 1, "Expected one inclusive upload bound"
    args = [
        "-m",
        "pytest",
        TEST,
        "-q",
        "--tb=short",
        "-k",
        "upload_byte_boundary_is_inclusive",
    ]
    before = run(output, "mutation-before.log", args)
    if before.returncode:
        raise RuntimeError("Baseline boundary tests failed; no mutation applied")
    mutated = None
    try:
        target.write_bytes(
            original.replace(needle, b"len(data) + len(chunk) >= maximum")
        )
        mutated = run(output, "mutation-killed.log", args)
    finally:
        target.write_bytes(original)
    restored = run(
        output, "mutation-restored.log", ["-m", "pytest", TEST, "-q", "--tb=short"]
    )
    result = {
        "file": str(target.relative_to(ROOT)).replace("\\", "/"),
        "operator": "> to >=",
        "expression": needle.decode(),
        "before_exit": before.returncode,
        "mutated_exit": None if mutated is None else mutated.returncode,
        "restored_exit": restored.returncode,
        "restored_bytes_match": original == target.read_bytes(),
        "api_sha256": hashlib.sha256(original).hexdigest(),
        "killed_by": "test_upload_byte_boundary_is_inclusive[0-202]",
    }
    write_json(output / "mutation.json", result)
    assert (
        result["mutated_exit"] == 1
        and restored.returncode == 0
        and result["restored_bytes_match"]
    )


def coverage(output):
    data = output / ".coverage"
    result = run(
        output,
        "coverage-suite.log",
        [
            "-m",
            "coverage",
            "run",
            "--branch",
            "--data-file",
            str(data),
            "--source",
            "backend/src/docintel",
            "-m",
            "pytest",
            TEST,
            "-q",
            "--tb=short",
        ],
    )
    assert result.returncode == 0
    result = run(
        output,
        "coverage-export.log",
        [
            "-m",
            "coverage",
            "json",
            "--data-file",
            str(data),
            "-o",
            str(output / "coverage.json"),
        ],
    )
    assert result.returncode == 0
    report = json.loads((output / "coverage.json").read_text(encoding="utf-8"))
    selected = []
    for name, entry in report["files"].items():
        normal = name.replace("\\", "/")
        if normal.endswith(
            ("services/documents.py", "api/documents.py", "repositories/sqlite.py")
        ):
            selected.append({"file": normal, **entry["summary"]})
    write_json(output / "coverage-summary.json", selected)


def repeat(output):
    results = []
    for number in range(1, 4):
        result = run(
            output, f"repeat-{number}.log", ["-m", "pytest", TEST, "-q", "--tb=short"]
        )
        results.append(
            {
                "order": "normal",
                "run": number,
                "exit": result.returncode,
                "summary": result.stdout.strip().splitlines()[-1],
            }
        )
        assert result.returncode == 0
    collected = run(
        output, "collection.log", ["-m", "pytest", TEST, "--collect-only", "-q"]
    )
    assert collected.returncode == 0
    # pytest reports IDs relative to its backend rootdir; invoke them from the repository root.
    ids = [
        TEST + "::" + line.strip().split("::", 1)[1]
        for line in collected.stdout.splitlines()
        if "::test_" in line
    ]
    assert len(ids) == 24
    result = run(
        output,
        "reverse-order.log",
        ["-m", "pytest", *reversed(ids), "-q", "--tb=short"],
    )
    results.append(
        {
            "order": "reverse",
            "run": 4,
            "exit": result.returncode,
            "summary": result.stdout.strip().splitlines()[-1],
        }
    )
    write_json(
        output / "repeat.json",
        {
            "results": results,
            "cases_per_run": len(ids),
            "controls": {
                "time_concurrency": "Barrier and Event; timeout only as a safety ceiling",
                "order_state": "Fresh tmp_path, fixture monkeypatch cleanup, reverse node order",
                "network": "In-process API tests; TCP load is separate; no WAN",
                "data": "Fixed synthetic PNG/pairwise order; UUIDs compared relationally",
            },
        },
    )
    assert result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", choices=("mutation", "coverage", "repeat"))
    parser.add_argument("--output", type=Path, default=ROOT / "runtime/vt042")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    {"mutation": mutation, "coverage": coverage, "repeat": repeat}[args.experiment](
        output
    )


if __name__ == "__main__":
    main()
