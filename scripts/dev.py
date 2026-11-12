"""One local entry point. All commands run at repository root and fail on errors."""

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UV = ["uv", "run", "--project", "backend", "--locked"]
NPM = ["npm", "--prefix", "frontend"]
BACKEND = [
    UV + ["ruff", "check", "backend", "scripts", "pipeline"],
    UV + ["ruff", "format", "--check", "backend", "scripts", "pipeline"],
    UV + ["pytest", "backend/tests", "pipeline/tests", "-q"],
    UV + ["python", "scripts/generate_contracts.py", "--check"],
    UV + ["python", "scripts/check_data.py"],
    UV + ["python", "scripts/check_repository.py"],
]
FRONTEND = [
    NPM + ["run", name]
    for name in (
        "contracts:check",
        "typecheck",
        "lint",
        "format:check",
        "test",
        "build",
    )
]
EVALUATION = [
    UV + ["python", "scripts/check_evaluation_regression.py"],
    UV
    + [
        "python",
        "scripts/evaluate_fixtures.py",
        "--output",
        "runtime/checks/fixture.json",
    ],
]


def run(command):
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    commands = {
        "setup": [["uv", "sync", "--project", "backend", "--locked"], NPM + ["ci"]],
        "models": [UV + ["python", "scripts/fetch_ocr_models.py"]],
        "backend": [
            UV
            + [
                "uvicorn",
                "docintel.api.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ]
        ],
        "frontend": [NPM + ["run", "dev"]],
        "backend-check": BACKEND,
        "frontend-check": FRONTEND,
        "evaluation-check": EVALUATION,
        "check": BACKEND + FRONTEND + EVALUATION,
        "ocr": [UV + ["python", "scripts/verify_product.py"]],
        "e2e": [NPM + ["run", "test:e2e"]],
    }
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=commands)
    args = parser.parse_args()
    for command in commands[args.command]:
        run(command)
    if args.command == "setup":
        destination = ROOT / ".env"
        if not destination.exists():
            shutil.copyfile(ROOT / ".env.example", destination)
            print("Created local .env from .env.example (not tracked).")
        else:
            print(
                "Kept existing .env; check provider/runtime settings before starting."
            )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
