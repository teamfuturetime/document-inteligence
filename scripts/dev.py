"""One local entry point. All commands run at repository root and fail on errors."""

import argparse
import os
import shutil
import subprocess
import sys
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
    executable = shutil.which(command[0])
    if executable is None:
        raise FileNotFoundError(f"Executable not found on PATH: {command[0]}")
    # Freeze relative PATH entries in the caller's cwd before changing to ROOT.
    resolved = [str(Path(executable).absolute()), *command[1:]]
    print("+ " + " ".join(resolved), flush=True)
    subprocess.run(resolved, cwd=ROOT, check=True, shell=False)


def main():
    if sys.argv[1:2] == ["doctor"]:
        # Use installed dependencies only: uv run/setup could install or mutate files.
        python = (
            ROOT
            / "backend/.venv"
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        environment = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": os.pathsep.join(
                str(ROOT / p) for p in ("backend/src", "pipeline/src")
            ),
        }
        try:
            result = subprocess.run(
                [
                    str(python) if python.is_file() else sys.executable,
                    "-c",
                    (
                        "import json,sys\n"
                        # This code must parse before importing the Python 3.14 backend.
                        "if sys.version_info < (3,14):\n"
                        " print(json.dumps({'report_version':1,'status':'action_required',"
                        "'checks':[{'name':'python','status':'action_required',"
                        "'code':'python_unsupported','action':'Use Python 3.14 or newer; "
                        "follow the Product CI pin and rerun doctor.'}]}))\n"
                        " sys.exit(1)\n"
                        "try:\n from docintel.doctor import main\n"
                        "except ImportError:\n"
                        " print(json.dumps({'report_version':1,'status':'action_required',"
                        "'checks':[{'name':'dependencies','status':'action_required',"
                        "'code':'dependencies_missing','action':'Install backend dependencies "
                        "with the explicit setup command; rerun doctor.'}]}))\n"
                        " sys.exit(1)\n"
                        "sys.exit(main())"
                    ),
                    *sys.argv[2:],
                ],
                cwd=ROOT,
                env=environment,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            print(
                '{"report_version":1,"status":"error","checks":[{"name":"doctor","status":"error","code":"launcher_failed","action":"Check installed backend dependencies and rerun doctor."}]}'
            )
            raise SystemExit(2) from None
        raise SystemExit(result.returncode)
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
                "--limit-concurrency",
                "16",
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
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Read-only diagnostics: python scripts/dev.py doctor [--json] [--runtime PATH]",
    )
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
