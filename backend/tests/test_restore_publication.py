"""Restored runtimes become visible only after copied bytes pass snapshot verification."""

import errno
import os
import shutil
import sqlite3
import stat
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

import pytest
from test_backup_verify import helper as helper
from test_backup_verify import tree
from test_backup_verify import valid_backup as valid_backup

from docintel.repositories.sqlite import DocumentRepository
from docintel.storage import publication
from docintel.storage.backup import BackupVerificationError, verify_backup


@pytest.mark.parametrize(
    "fault",
    ["database", "source", "preview", "manifest", "verify", "remove_manifest", "fsync", "publish"],
)
def test_restore_failure_keeps_source_and_final_absent(
    valid_backup, helper, tmp_path, monkeypatch, fault
):
    source = valid_backup
    before = tree(source)
    destination = tmp_path / "published-runtime"
    root = OSError(errno.ENOSPC, "synthetic restore write failure")
    if fault in {"database", "source", "preview"}:
        copy = shutil.copyfile
        suffix = ".sqlite3" if fault == "database" else "." + fault

        def copy_file(src, target, *a, **kw):
            if src.suffix == suffix:
                raise root
            return copy(src, target, *a, **kw)

        monkeypatch.setattr(helper.shutil, "copyfile", copy_file)
    elif fault == "manifest":
        write = Path.write_bytes

        def write_manifest(path, *a, **kw):
            if path.name == "backup.json":
                raise root
            return write(path, *a, **kw)

        monkeypatch.setattr(Path, "write_bytes", write_manifest)
    elif fault == "verify":
        verify = helper.verify_backup

        def verifier(path):
            if path != source:
                raise BackupVerificationError("SYNTHETIC_STAGED_FAILURE")
            return verify(path)

        monkeypatch.setattr(helper, "verify_backup", verifier)
    elif fault == "remove_manifest":
        unlink = Path.unlink

        def remove(path, *a, **kw):
            if path.name == "backup.json":
                raise root
            return unlink(path, *a, **kw)

        monkeypatch.setattr(Path, "unlink", remove)
    elif fault == "fsync":
        monkeypatch.setattr(helper, "sync_files", lambda _: (_ for _ in ()).throw(root))
    else:
        monkeypatch.setattr(helper, "publish_directory", lambda *_: (_ for _ in ()).throw(root))
    with pytest.raises((OSError, BackupVerificationError)) as failure:
        helper.restore(source, destination)
    if fault == "verify":
        assert isinstance(failure.value, BackupVerificationError)
    else:
        assert failure.value is root
    assert not destination.exists() and tree(source) == before
    assert not list(tmp_path.glob(".docintel-staging-*"))


@pytest.mark.parametrize("suffix", [".sqlite3", ".source", ".preview"])
def test_corrupted_copy_is_reverified_before_publication(
    valid_backup, helper, tmp_path, monkeypatch, suffix
):
    original = helper.shutil.copyfile
    before = tree(valid_backup)

    def corrupt(src, target, *a, **kw):
        result = original(src, target, *a, **kw)
        if src.suffix == suffix:
            target.write_bytes(b"synthetic corrupt copied bytes")
        return result

    monkeypatch.setattr(helper.shutil, "copyfile", corrupt)
    with pytest.raises(BackupVerificationError):
        helper.restore(valid_backup, tmp_path / "final")
    assert not (tmp_path / "final").exists() and tree(valid_backup) == before
    assert not list(tmp_path.glob(".docintel-staging-*"))


@pytest.mark.parametrize("entry", ["file", "directory", "dangling"])
def test_late_destination_cannot_be_overwritten_by_restore(
    valid_backup, helper, tmp_path, monkeypatch, entry
):
    publish = helper.publish_directory
    destination = tmp_path / "late runtime"
    target = tmp_path / "alias target"

    def create_late(staged, final):
        assert not (staged / "backup.json").exists()
        if entry == "file":
            final.write_bytes(b"keep")
        elif entry == "directory":
            final.mkdir()
        else:
            target.mkdir()
            if os.name == "nt":
                subprocess.run(
                    ["cmd.exe", "/d", "/c", "mklink", "/J", str(final), str(target)],
                    capture_output=True,
                    check=True,
                )
            else:
                final.symlink_to(target, target_is_directory=True)
            target.rename(tmp_path / "moved alias target")
        return publish(staged, final)

    monkeypatch.setattr(helper, "publish_directory", create_late)
    with pytest.raises(FileExistsError):
        helper.restore(valid_backup, destination)
    if entry == "file":
        assert destination.read_bytes() == b"keep"
    elif entry == "directory":
        assert list(destination.iterdir()) == []
    else:
        destination.lstat()
        assert not target.exists()
    assert not list(tmp_path.glob(".docintel-staging-*"))


def test_two_restore_helpers_race_without_replacement(valid_backup, helper, tmp_path, monkeypatch):
    publish = helper.publish_directory
    barrier = threading.Barrier(2, timeout=10)
    final = tmp_path / "race runtime"

    def race(staged, destination):
        barrier.wait()
        return publish(staged, destination)

    monkeypatch.setattr(helper, "publish_directory", race)

    def attempt():
        try:
            helper.restore(valid_backup, final)
            return "published"
        except FileExistsError:
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(outcomes) == ["published", "refused"]
    expected = {
        relative: path.read_bytes() for relative, path in verify_backup(valid_backup).entries
    }
    assert tree(final) == expected
    assert not list(tmp_path.glob(".docintel-staging-*"))


@pytest.mark.parametrize("schema", [1, 2])
def test_verified_restore_retains_schema_shape_and_private_modes(
    valid_backup, helper, tmp_path, monkeypatch, schema
):
    source = valid_backup
    if schema == 2:
        runtime = tmp_path / "empty schema2"
        DocumentRepository(runtime / "documents.sqlite3").initialize()
        source = tmp_path / "schema2 backup"
        helper.backup(runtime, source)
    before = tree(source)

    def prohibited(*_):
        pytest.fail("restore must not initialize or migrate a runtime")

    monkeypatch.setattr(DocumentRepository, "initialize", prohibited)
    final = tmp_path / "restored"
    expected = {relative: path.read_bytes() for relative, path in verify_backup(source).entries}
    helper.restore(source, final)
    assert tree(final) == expected and tree(source) == before
    assert not (final / "backup.json").exists()
    with closing(
        sqlite3.connect((final / "documents.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        assert db.execute("SELECT max(version) FROM schema_migrations").fetchone() == (schema,)
    if os.name == "posix":
        assert stat.S_IMODE(final.stat().st_mode) == 0o700
        for relative in expected:
            assert stat.S_IMODE((final / relative).stat().st_mode) == 0o600


def test_restore_cleanup_error_does_not_mask_root_or_delete_other_staging(
    valid_backup, helper, tmp_path, monkeypatch, caplog
):
    root = OSError("PRIVATE_CANARY fsync")
    before = tree(valid_backup)
    unrelated = tmp_path / ".docintel-staging-unrelated"
    unrelated.mkdir()
    (unrelated / "keep").write_bytes(b"keep")
    monkeypatch.setattr(helper, "sync_files", lambda _: (_ for _ in ()).throw(root))
    remove = publication.shutil.rmtree

    def fail_cleanup(path, *a, **kw):
        if Path(path).name.startswith(".docintel-staging-"):
            raise PermissionError("PRIVATE_CANARY cleanup")
        return remove(path, *a, **kw)

    monkeypatch.setattr(publication.shutil, "rmtree", fail_cleanup)
    with pytest.raises(OSError) as exc:
        helper.restore(valid_backup, tmp_path / "final")
    assert exc.value is root and not (tmp_path / "final").exists()
    assert (unrelated / "keep").read_bytes() == b"keep" and tree(valid_backup) == before
    assert "staging retained" in caplog.text and "PRIVATE_CANARY" not in caplog.text


def test_restore_lost_ack_retains_complete_final(valid_backup, helper, tmp_path, monkeypatch):
    publish = helper.publish_directory
    final = tmp_path / "published-runtime"
    expected = {
        relative: path.read_bytes() for relative, path in verify_backup(valid_backup).entries
    }

    def lost_ack(source, destination):
        publish(source, destination)
        raise OSError("synthetic lost publication acknowledgement")

    monkeypatch.setattr(helper, "publish_directory", lost_ack)
    with pytest.raises(OSError):
        helper.restore(valid_backup, final)
    assert tree(final) == expected and not list(tmp_path.glob(".docintel-staging-*"))


def test_restore_rejects_destination_inside_backup_before_staging(valid_backup, helper):
    before = tree(valid_backup)
    with pytest.raises(ValueError, match="outside"):
        helper.restore(valid_backup, valid_backup / "nested" / "runtime")
    assert tree(valid_backup) == before and not (valid_backup / "nested").exists()


@pytest.mark.parametrize("failed", [False, True])
def test_cli_reports_restore_verified_only_after_success(
    valid_backup, helper, tmp_path, monkeypatch, capsys, failed
):
    final = tmp_path / "published-runtime"
    monkeypatch.setattr(
        "sys.argv", ["backup_runtime.py", str(valid_backup), str(final), "--restore"]
    )
    if failed:
        monkeypatch.setattr(
            helper,
            "publish_directory",
            lambda *_: (_ for _ in ()).throw(OSError("synthetic publish failure")),
        )
        with pytest.raises(OSError):
            helper.main()
        assert "Restore verified" not in capsys.readouterr().out and not final.exists()
    else:
        helper.main()
        assert "Restore verified" in capsys.readouterr().out and final.is_dir()


def test_restore_uses_original_verified_manifest_when_source_metadata_changes(
    valid_backup, helper, tmp_path, monkeypatch
):
    expected = {
        relative: path.read_bytes() for relative, path in verify_backup(valid_backup).entries
    }
    copy = helper.shutil.copyfile

    def change_metadata_after_initial_validation(source, target, *a, **kw):
        result = copy(source, target, *a, **kw)
        if source.name == "documents.sqlite3":
            (valid_backup / "backup.json").write_bytes(b"synthetic concurrent metadata corruption")
        return result

    monkeypatch.setattr(helper.shutil, "copyfile", change_metadata_after_initial_validation)
    helper.restore(valid_backup, tmp_path / "published-runtime")
    assert tree(tmp_path / "published-runtime") == expected
