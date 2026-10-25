import hashlib
import importlib.metadata
import platform
import subprocess
import sys
from pathlib import Path


def runtime_metadata() -> dict:
    root = Path(__file__).parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in {".py", ".json"}:
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    commit = dirty = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, timeout=2, check=False
        )
        if result.returncode == 0:
            commit = result.stdout.decode("ascii").strip()
            state = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                timeout=2,
                check=False,
            )
            dirty = bool(state.stdout) if state.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {
        "git_commit": commit,
        "git_dirty": dirty,
        "pipeline_source_sha256": digest.hexdigest(),
        "runtime": {
            "python": sys.version.split()[0],
            "pillow": importlib.metadata.version("pillow"),
            "pydantic": importlib.metadata.version("pydantic"),
        },
        "hardware": {
            "architecture": platform.machine(),
            "processor": platform.processor() or "unknown",
            "platform": platform.system(),
            "acceleration": "CPU",
        },
        "reproducibility_limitations": ["OCR confidence is heuristic, not calibrated"],
    }
