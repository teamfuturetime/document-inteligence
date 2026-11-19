"""Offline, read-only diagnostics. Never initialize services or repair configuration."""

import argparse
import json
import platform
import re
import shutil
import sqlite3
import subprocess
import time
from contextlib import closing
from pathlib import Path

from docintel.config import ROOT, Settings

ACTIONS = {
    "ready": "No action required.",
    "tool_missing": "Install the tool using README prerequisites; rerun doctor.",
    "tool_version": "Use the version pinned in Product CI; rerun doctor.",
    "tool_failed": "Check the tool installation; rerun doctor.",
    "tool_timeout": "The version probe timed out; check the tool installation.",
    "runtime_missing": "Select a new runtime explicitly when starting the app.",
    "runtime_empty": "The runtime is empty; the app can initialize it on explicit startup.",
    "database_missing": "Preserve existing files; select the correct runtime or verified backup.",
    "database_empty": "Preserve the empty database; select the correct runtime or verified backup.",
    "schema1_empty": "Empty schema 1 can upgrade on explicit app startup; doctor does not upgrade.",
    "migration_required": "Stop the app; follow the offline backup/migration runbook.",
    "future_schema": "Use a compatible application; do not downgrade or edit schema versions.",
    "database_invalid": "Preserve this runtime; restore a verified backup into a new directory.",
    "offline_required": "Stop the app; finish SQLite recovery/checkpoint before probing.",
    "config_invalid": "Check local/session settings against .env.example; configuration unchanged.",
    "provider_unconfigured": "Choose an explicit provider profile in .env before startup.",
    "fixture_only": "Fixture mode is for contract demonstrations; select Tesseract for native OCR.",
    "models_unavailable": "Check model files/checksums; use the explicit models command if needed.",
    "engine_unavailable": "Configure a working Tesseract 5 executable; no OCR was run.",
    "unreadable": "Check read permissions; no files were changed.",
}


def check(name, code="ready", status="ready", **details):
    return {"name": name, "status": status, "code": code, "action": ACTIONS[code], **details}


def tool_check(name, expected, executable=None):
    executable = shutil.which(executable or name)
    if not executable:
        return check(name, "tool_missing", "action_required", expected=expected)
    try:
        result = subprocess.run(
            [str(Path(executable).absolute()), "--version"],
            capture_output=True,
            timeout=3,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return check(name, "tool_timeout", "error", expected=expected)
    except OSError:
        return check(name, "tool_failed", "error", expected=expected)
    # Only emit a numeric version, never raw stdout/stderr, paths or exception text.
    match = re.match(rb"(?:v|uv |tesseract v?)?(\d+\.\d+\.\d+)(?:\s|$)", result.stdout)
    if result.returncode or match is None:
        return check(name, "tool_failed", "error", expected=expected)
    actual = match[1].decode("ascii")
    valid = actual.startswith("5.") if expected == "5.x" else actual == expected
    return check(
        name,
        "ready" if valid else "tool_version",
        "ready" if valid else "action_required",
        expected=expected,
        observed=actual,
    )


def tool_pins():
    """Read existing CI pins rather than maintaining a second toolchain inventory."""
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    patterns = {
        "python": r'python-version: "([\d.]+)"',
        "node": r'node-version: "([\d.]+)"',
        "npm": r"npm install --global npm@([\d.]+)",
        "uv": r'^\s+version: "([\d.]+)"',
    }
    pins = {}
    for name, pattern in patterns.items():
        values = set(re.findall(pattern, workflow, re.M))
        if len(values) != 1:
            raise ValueError("Ambiguous toolchain pin")
        pins[name] = values.pop()
    return pins


def runtime_check(runtime):
    try:
        if not runtime.exists():
            return check("runtime", "runtime_missing", "action_required")
        if not runtime.is_dir():
            return check("runtime", "database_invalid", "error")
        database = runtime / "documents.sqlite3"
        if not database.exists():
            empty = next(runtime.iterdir(), None) is None
            return check(
                "runtime", "runtime_empty" if empty else "database_missing", "action_required"
            )
        if not database.is_file():
            return check("runtime", "database_invalid", "error")
        # Immutable ro avoids SQLite creating shm/journal files. Never ignore pending WAL.
        if any(Path(str(database) + suffix).exists() for suffix in ("-wal", "-journal")):
            return check("runtime", "offline_required", "action_required")
        if database.stat().st_size == 0:
            return check("runtime", "database_empty", "action_required")
        deadline = time.monotonic() + 3
        with closing(
            sqlite3.connect(
                database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True, timeout=1
            )
        ) as db:
            db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
            db.execute("PRAGMA query_only=ON")
            if db.execute("PRAGMA quick_check(1)").fetchone() != ("ok",):
                return check("runtime", "database_invalid", "error")
            version = db.execute("SELECT max(version) FROM schema_migrations").fetchone()[0]
            if type(version) is not int or version < 1:
                return check("runtime", "database_invalid", "error")
            if version > 2:
                return check("runtime", "future_schema", "error", schema_version=version)
            # Validate essential structure without reading any account/session/field values.
            for table in ("documents", "runs", "revisions", "events"):
                db.execute(f"SELECT 1 FROM {table} LIMIT 0")
            if version == 1:
                populated = db.execute("SELECT 1 FROM documents LIMIT 1").fetchone() is not None
                return check(
                    "runtime",
                    "migration_required" if populated else "schema1_empty",
                    "action_required",
                    schema_version=1,
                )
            db.execute("SELECT owner_id FROM documents LIMIT 0")
            for table in ("users", "sessions", "login_budget"):
                db.execute(f"SELECT 1 FROM {table} LIMIT 0")
            return check("runtime", schema_version=2)
    except sqlite3.Error:
        return check("runtime", "database_invalid", "error")
    except OSError:
        return check("runtime", "unreadable", "error")


def diagnose(runtime=None):
    checks = []
    try:
        pins = tool_pins()
        actual = platform.python_version()
        checks.append(
            check(
                "python",
                "ready" if actual == pins["python"] else "tool_version",
                "ready" if actual == pins["python"] else "action_required",
                expected=pins["python"],
                observed=actual,
            )
        )
        checks.extend(tool_check(name, pins[name]) for name in ("uv", "node", "npm"))
    except OSError, ValueError:
        checks.append(check("toolchain", "config_invalid", "error"))
    try:
        settings = Settings()
    except ValueError, OSError:
        checks.append(check("config", "config_invalid", "error"))
        if runtime is not None:
            checks.append(runtime_check(runtime))
    else:
        checks.append(
            check("config", auth_mode=settings.auth_mode, provider_mode=settings.provider_mode)
        )
        checks.append(runtime_check(runtime if runtime is not None else settings.runtime_dir))
        if settings.provider_mode == "unconfigured":
            checks.append(check("provider", "provider_unconfigured", "action_required"))
        elif settings.provider_mode == "fixture":
            checks.append(check("provider", "fixture_only", "action_required"))
        else:
            from document_pipeline.errors import PipelineError
            from document_pipeline.tesseract import verify_models

            checks.append(tool_check("tesseract", "5.x", settings.tesseract_executable))
            try:
                verify_models(settings.tessdata_dir)
            except PipelineError, OSError:
                checks.append(check("models", "models_unavailable", "action_required"))
            else:
                checks.append(check("models"))
    status = (
        "error"
        if any(c["status"] == "error" for c in checks)
        else "action_required"
        if any(c["status"] == "action_required" for c in checks)
        else "ready"
    )
    return {"report_version": 1, "status": status, "checks": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit only versioned JSON")
    parser.add_argument(
        "--runtime", type=Path, help="Probe this offline runtime instead of configured runtime"
    )
    args = parser.parse_args()
    report = diagnose(args.runtime)
    if args.json:
        print(json.dumps(report, ensure_ascii=True))
    else:
        print(f"Doctor v1: {report['status']}")
        for item in report["checks"]:
            print(f"{item['name']}: {item['code']} — {item['action']}")
    return {"ready": 0, "action_required": 1, "error": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
