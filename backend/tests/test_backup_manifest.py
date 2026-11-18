"""Reject unusable backup manifests without publishing an empty runtime."""

import importlib.util
import json

import pytest

from docintel.config import ROOT


@pytest.fixture
def backup_module():
    spec = importlib.util.spec_from_file_location(
        "backup_runtime", ROOT / "scripts/backup_runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "manifest",
    [
        {"version": 1, "sha256": {}},
        {"version": 1, "sha256": {"documents/file.source": "0" * 64}},
        {"version": 2, "sha256": {"documents.sqlite3": "0" * 64}},
        {"version": True, "sha256": {"documents.sqlite3": "0" * 64}},
        {"version": "1", "sha256": {"documents.sqlite3": "0" * 64}},
        {"sha256": {"documents.sqlite3": "0" * 64}},
        {"version": 1},
        {"version": 1, "sha256": []},
        {"version": 1, "sha256": {"documents.sqlite3": None}},
        {"version": 1, "sha256": {"documents.sqlite3": "not-a-hash"}},
        {"version": 1, "sha256": {"documents.sqlite3": "g" * 64}},
        [],
        None,
    ],
)
def test_invalid_manifest_never_creates_runtime(backup_module, tmp_path, manifest):
    source = tmp_path / "backup"
    source.mkdir()
    (source / "backup.json").write_text(json.dumps(manifest))
    destination = tmp_path / "restored"

    with pytest.raises(ValueError, match="manifest"):
        backup_module.restore(source, destination)

    assert not destination.exists()


@pytest.mark.parametrize("relative", ["../outside", "/absolute", "nested/../../outside", ""])
def test_invalid_entry_path_does_not_create_runtime(backup_module, tmp_path, relative):
    source = tmp_path / "backup"
    source.mkdir()
    database = source / "documents.sqlite3"
    database.write_bytes(b"database-content")
    manifest = {
        "version": 1,
        "sha256": {"documents.sqlite3": backup_module.sha256(database), relative: "0" * 64},
    }
    (source / "backup.json").write_text(json.dumps(manifest))
    destination = tmp_path / "restored"

    with pytest.raises(ValueError):
        backup_module.restore(source, destination)

    assert not destination.exists()


def test_unsupported_cli_backup_never_reports_verified(
    backup_module, tmp_path, monkeypatch, capsys
):
    source = tmp_path / "backup"
    source.mkdir()
    (source / "backup.json").write_text('{"version":1,"sha256":{}}')
    destination = tmp_path / "restored"
    monkeypatch.setattr(
        "sys.argv", ["backup_runtime.py", str(source), str(destination), "--restore"]
    )

    with pytest.raises(ValueError, match="manifest"):
        backup_module.main()

    assert "Restore verified" not in capsys.readouterr().out
    assert not destination.exists()
