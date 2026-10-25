"""Record the exact local candidate without pretending uncommitted work has a new Git SHA."""

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from docintel import __version__
from docintel.config import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    names = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
        )
        .decode("utf-8")
        .split("\0")
    )
    selected = {}
    for name in sorted(set(names)):
        if not name.startswith(
            (
                "backend/",
                "frontend/",
                "pipeline/",
                "scripts/",
                "configs/",
                "contracts/",
                "data/",
            )
        ) and name not in {
            "compose.yaml",
            ".github/workflows/ci.yml",
            ".env.example",
            ".gitignore",
            ".gitattributes",
        }:
            continue
        path = (ROOT / name).resolve()
        if path.is_file() and path.is_relative_to(ROOT):
            selected[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    commit = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    )
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
    result = {
        "app_version": __version__,
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": commit,
        "git_dirty": dirty,
        "sha256": selected,
        "note": "Local working-tree candidate; user commits/pushes separately; models/runtime excluded",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Candidate snapshot: {len(selected)} files; dirty={dirty}")


if __name__ == "__main__":
    main()
