"""Chạy checks nền, dừng ngay khi fail và giữ record lệnh/thời điểm thực tế."""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime

from docintel.config import ROOT

npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
if npm is None:
    raise SystemExit("npm is unavailable; frontend checks not verified")
checks = [
    ("backend-lint", [sys.executable, "-m", "ruff", "check", "backend", "scripts"]),
    (
        "backend-format",
        [sys.executable, "-m", "ruff", "format", "--check", "backend", "scripts"],
    ),
    ("backend-tests", [sys.executable, "-m", "pytest", "backend/tests", "-q"]),
    ("backend-contracts", [sys.executable, "scripts/generate_contracts.py", "--check"]),
    ("fixture-manifest", [sys.executable, "scripts/check_data.py"]),
    ("fixture-evaluator", [sys.executable, "scripts/evaluate_fixtures.py"]),
    ("repository", [sys.executable, "scripts/check_repository.py"]),
    ("frontend-frozen-install", [npm, "--prefix", "frontend", "ci"]),
    *[
        ("frontend-" + task, [npm, "--prefix", "frontend", "run", task])
        for task in (
            "contracts:check",
            "typecheck",
            "lint",
            "format:check",
            "test",
            "build",
        )
    ],
]
records = []
environment = {**os.environ, "PYTHONUTF8": "1"}
output = ROOT / "runtime/verification-local.json"
output.parent.mkdir(parents=True, exist_ok=True)
for name, command in checks:
    started = datetime.now(UTC).isoformat()
    begin = time.monotonic()
    print(f"\nRunning {name}", flush=True)
    result = subprocess.run(command, cwd=ROOT, env=environment, check=False)
    records.append(
        {
            "check": name,
            "command": command,
            "started_at": started,
            "duration_seconds": round(time.monotonic() - begin, 3),
            "status": "pass" if result.returncode == 0 else "fail",
            "exit_code": result.returncode,
        }
    )
    output.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if result.returncode:
        raise SystemExit(result.returncode)
print(
    f"\nFOUNDATION CHECKS PASS: {len(records)} checks; Docker/remote CI/model excluded."
)
