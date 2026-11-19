"""Doctor must inspect offline snapshots without repairing or disclosing their content."""

import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from importlib.resources import files

import pytest

from docintel import doctor
from docintel.config import ROOT, Settings
from docintel.repositories.sqlite import DocumentRepository


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def legacy(runtime, populated=False):
    runtime.mkdir()
    with closing(sqlite3.connect(runtime / "documents.sqlite3")) as db, db:
        db.executescript(
            files("docintel").joinpath("repositories/migrations/001_documents.sql").read_text()
        )
        db.execute("INSERT INTO schema_migrations VALUES(1,'historical')")
        if populated:
            db.execute(
                "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    "a" * 32,
                    "hoa_don",
                    "secret_filename",
                    "synthetic",
                    "0" * 64,
                    1,
                    1,
                    "now",
                    "run",
                    None,
                ),
            )


@pytest.mark.parametrize(
    "state,code",
    [
        ("missing", "runtime_missing"),
        ("empty", "runtime_empty"),
        ("assets", "database_missing"),
        ("zero", "database_empty"),
        ("corrupt", "database_invalid"),
        ("db1_empty", "schema1_empty"),
        ("db1", "migration_required"),
        ("db2", "ready"),
        ("future", "future_schema"),
        ("wal", "offline_required"),
        ("journal", "offline_required"),
        ("unversioned", "database_invalid"),
    ],
)
def test_runtime_states_leave_tree_unchanged(tmp_path, state, code):
    runtime = tmp_path / "runtime"
    if state in {"db1", "db1_empty"}:
        legacy(runtime, state == "db1")
    elif state in {"db2", "future", "wal", "journal"}:
        DocumentRepository(runtime / "documents.sqlite3").initialize()
        if state == "future":
            with closing(sqlite3.connect(runtime / "documents.sqlite3")) as db, db:
                db.execute("INSERT INTO schema_migrations VALUES(3,'future')")
        if state in {"wal", "journal"}:
            (runtime / ("documents.sqlite3-" + state)).write_bytes(b"preserve pending data")
    elif state != "missing":
        runtime.mkdir()
        if state == "assets":
            (runtime / "private.source").write_bytes(b"private source")
        elif state in {"zero", "corrupt"}:
            (runtime / "documents.sqlite3").write_bytes(
                b"not sqlite" if state == "corrupt" else b""
            )
        elif state == "unversioned":
            with closing(sqlite3.connect(runtime / "documents.sqlite3")) as db, db:
                db.execute("CREATE TABLE documents(id TEXT)")
    (tmp_path / ".env").write_text("PRIVATE_CANARY=never_emit\n")
    before = snapshot(tmp_path)
    result = doctor.runtime_check(runtime)
    assert result["code"] == code
    assert snapshot(tmp_path) == before
    assert "secret" not in json.dumps(result) and str(tmp_path) not in json.dumps(result)
    if state == "missing":
        assert not runtime.exists()


@pytest.mark.parametrize(
    "outcome,code",
    [
        ("missing", "tool_missing"),
        ("timeout", "tool_timeout"),
        ("error", "tool_failed"),
        ("bad", "tool_failed"),
        ("version", "tool_version"),
        ("good", "ready"),
    ],
)
def test_tool_probes_are_bounded_and_redacted(monkeypatch, outcome, code):
    monkeypatch.setattr(
        doctor.shutil, "which", lambda _: None if outcome == "missing" else "/private/tools/npm"
    )

    def run(argv, **kw):
        assert kw["timeout"] == 3 and kw["capture_output"] and not kw.get("shell", False)
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(argv, 3, output=b"PRIVATE_CANARY")
        if outcome == "error":
            raise OSError("PRIVATE_CANARY")
        stdout = (
            b"11.13.0\n"
            if outcome == "good"
            else b"1.2.3\n"
            if outcome == "version"
            else b"PRIVATE_CANARY"
        )
        return subprocess.CompletedProcess(argv, 0, stdout, b"PRIVATE_CANARY")

    monkeypatch.setattr(doctor.subprocess, "run", run)
    result = doctor.tool_check("npm", "11.13.0")
    assert result["code"] == code
    assert "PRIVATE_CANARY" not in json.dumps(result)
    assert "/private" not in json.dumps(result)


@pytest.mark.parametrize(
    "provider,code",
    [
        ("unconfigured", "provider_unconfigured"),
        ("fixture", "fixture_only"),
        ("tesseract", "ready"),
    ],
)
def test_provider_profiles_and_safe_config(monkeypatch, tmp_path, provider, code):
    settings = Settings(
        _env_file=None,
        provider_mode=provider,
        auth_mode="session",
        runtime_dir=tmp_path / "missing",
    )
    monkeypatch.setattr(doctor, "Settings", lambda: settings)
    monkeypatch.setattr(doctor, "tool_check", lambda name, *a: doctor.check(name))
    from document_pipeline import tesseract

    monkeypatch.setattr(tesseract, "verify_models", lambda _: {})
    result = doctor.diagnose()
    assert next(c for c in result["checks"] if c["name"] == "config")["auth_mode"] == "session"
    assert result["checks"][-1]["code"] == code
    assert str(tmp_path) not in json.dumps(result)


def test_invalid_config_does_not_echo_validation_inputs(monkeypatch, tmp_path):
    def invalid():
        raise ValueError("PRIVATE_CANARY configuration path")

    monkeypatch.setattr(doctor, "Settings", invalid)
    monkeypatch.setattr(doctor, "tool_check", lambda name, *a: doctor.check(name))
    result = doctor.diagnose(tmp_path / "missing")
    assert result["status"] == "error"
    assert "PRIVATE_CANARY" not in json.dumps(result)
    assert any(c["code"] == "runtime_missing" for c in result["checks"])


def test_real_cli_missing_runtime_never_creates_it(tmp_path):
    runtime = tmp_path / "not created"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/dev.py"),
            "doctor",
            "--json",
            "--runtime",
            str(runtime),
        ],
        env={**os.environ, "DOCINTEL_PROVIDER_MODE": "fixture"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    report = json.loads(result.stdout)
    assert report["report_version"] == 1 and result.returncode in {1, 2}
    assert any(c["code"] == "runtime_missing" for c in report["checks"])
    assert not runtime.exists()
    assert not result.stderr


def test_pins_match_current_ci():
    assert doctor.tool_pins() == {
        "python": "3.14.5",
        "node": "24.16.0",
        "npm": "11.13.0",
        "uv": "0.12.22",
    }


@pytest.mark.parametrize("bad_hash", [False, True])
def test_tesseract_models_missing_or_corrupt_are_actionable(monkeypatch, tmp_path, bad_hash):
    settings = Settings(_env_file=None, provider_mode="tesseract", tessdata_dir=tmp_path)
    if bad_hash:
        for name in ("vie", "eng"):
            (tmp_path / (name + ".traineddata")).write_bytes(b"PRIVATE_CANARY")
    monkeypatch.setattr(doctor, "Settings", lambda: settings)
    monkeypatch.setattr(doctor, "tool_check", lambda name, *a: doctor.check(name))
    result = doctor.diagnose(tmp_path / "missing")
    assert result["checks"][-1]["code"] == "models_unavailable"
    assert "PRIVATE_CANARY" not in json.dumps(result)


@pytest.mark.parametrize("state,code", [("db1", "migration_required"), ("db2", "ready")])
def test_real_cli_db_and_source_remain_unchanged(tmp_path, state, code):
    runtime = tmp_path / "runtime"
    if state == "db1":
        legacy(runtime, True)
    else:
        DocumentRepository(runtime / "documents.sqlite3").initialize()
    (runtime / "private.source").write_bytes(b"PRIVATE_CANARY")
    env_file = ROOT / ".env"
    before_env = env_file.read_bytes() if env_file.exists() else None
    before = snapshot(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/dev.py"),
            "doctor",
            "--json",
            "--runtime",
            str(runtime),
        ],
        env={**os.environ, "DOCINTEL_PROVIDER_MODE": "fixture"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    report = json.loads(result.stdout)
    assert next(c for c in report["checks"] if c["name"] == "runtime")["code"] == code
    assert snapshot(tmp_path) == before
    assert (env_file.read_bytes() if env_file.exists() else None) == before_env
    assert "PRIVATE_CANARY" not in result.stdout and not result.stderr


@pytest.mark.parametrize("status,exit_code", [("ready", 0), ("action_required", 1), ("error", 2)])
def test_json_exit_contract(monkeypatch, capsys, status, exit_code):
    monkeypatch.setattr(
        doctor, "diagnose", lambda _: {"report_version": 1, "status": status, "checks": []}
    )
    monkeypatch.setattr("sys.argv", ["doctor", "--json"])
    assert doctor.main() == exit_code
    assert json.loads(capsys.readouterr().out)["status"] == status
