"""Re-run collected contracts in three deterministic shuffled orders."""
from pathlib import Path
import random
import subprocess
import sys


root = Path(__file__).resolve().parents[2]
collected = subprocess.run([
    sys.executable, "-m", "pytest", "-o", "addopts=", "--collect-only", "-q", "individual/VT044/test_lifecycle.py",
], cwd=root, text=True, capture_output=True, check=True)
nodes = [line.strip() for line in collected.stdout.splitlines() if line.startswith("individual/VT044/test_lifecycle.py::")]
assert len(nodes) >= 28, collected.stdout
for seed in (44, 1945, 23001945):
    order = nodes.copy()
    random.Random(seed).shuffle(order)
    print(f"seed={seed}; cases={len(order)}", flush=True)
    run = subprocess.run([sys.executable, "-m", "pytest", "-q", *order], cwd=root, text=True, capture_output=True)
    print(run.stdout, run.stderr, flush=True)
    if run.returncode:
        raise SystemExit(run.returncode)
