"""Repeat focused tests in fresh processes and reversed order; bounded watchdog."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    with tempfile.TemporaryDirectory(prefix="vt046-order-") as directory:
        Path(directory, "vt046_reverse.py").write_text(
            "def pytest_collection_modifyitems(items):\n    items.reverse()\n")
        for order in ("normal", "reverse"):
            for run in range(1, 4):
                command = [sys.executable, "-m", "pytest", "backend/tests/test_notifications.py", "-q"]
                if order == "reverse":
                    command += ["-p", "vt046_reverse"]
                env = {**os.environ, "PYTHONPATH": directory + os.pathsep + os.environ.get("PYTHONPATH", "")}
                result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                        capture_output=True, timeout=30)
                print(f"order={order} run={run} exit={result.returncode}", flush=True)
                print(result.stdout, flush=True)
                if result.returncode != 0:
                    print(result.stderr)
                    return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
