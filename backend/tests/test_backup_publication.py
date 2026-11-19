"""Faults/races must never expose a partial or overwritten final snapshot."""

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
from test_auth_cli import prepare_legacy
from test_backup_verify import helper as helper
from test_backup_verify import tree

from docintel.repositories.sqlite import DocumentRepository
from docintel.storage import publication
from docintel.storage.backup import BackupVerificationError, verify_backup


@pytest.fixture
def runtime(tmp_path):
    source = tmp_path / "runtime"
    prepare_legacy(source)
    return source


@pytest.mark.parametrize(
    "fault", ["database", "source", "preview", "manifest", "fsync", "verify", "publish"]
)
def test_backup_failure_does_not_publish_partial_or_modify_source(
    runtime, helper, tmp_path, monkeypatch, fault
):
    before = tree(runtime)
    destination = tmp_path / "final snapshot"
    root = OSError(errno.ENOSPC, "synthetic stage failure")
    if fault == "database":
        connect = sqlite3.connect

        class BrokenSource:
            def __init__(self, db):
                self.db = db

            def close(self):
                self.db.close()

            def backup(self, _):
                raise root

        def database(*a, **kw):
            connection = connect(*a, **kw)
            return BrokenSource(connection) if kw.get("uri") else connection

        monkeypatch.setattr(helper.sqlite3, "connect", database)
    elif fault in {"source", "preview"}:
        copy = shutil.copyfile

        def copy_file(source, target, *a, **kw):
            if source.suffix == "." + fault:
                raise root
            return copy(source, target, *a, **kw)

        monkeypatch.setattr(helper.shutil, "copyfile", copy_file)
    elif fault == "manifest":
        write = Path.write_text

        def manifest(path, *a, **kw):
            if path.name == "backup.json":
                raise root
            return write(path, *a, **kw)

        monkeypatch.setattr(Path, "write_text", manifest)
    elif fault == "fsync":
        monkeypatch.setattr(publication.os, "fsync", lambda _: (_ for _ in ()).throw(root))
    elif fault == "verify":
        monkeypatch.setattr(
            helper,
            "verify_backup",
            lambda _: (_ for _ in ()).throw(BackupVerificationError("SYNTHETIC_FAILURE")),
        )
    else:
        monkeypatch.setattr(helper, "publish_directory", lambda *_: (_ for _ in ()).throw(root))
    with pytest.raises((OSError, BackupVerificationError)) as failure:
        helper.backup(runtime, destination)
    if fault == "verify":
        assert isinstance(failure.value, BackupVerificationError)
    else:
        assert failure.value is root
    assert not destination.exists() and tree(runtime) == before
    assert not list(tmp_path.glob(".docintel-staging-*"))


@pytest.mark.parametrize("entry", ["file", "directory", "dangling"])
def test_destination_created_after_verify_is_never_replaced(
    runtime, helper, tmp_path, monkeypatch, entry
):
    destination = tmp_path / "late destination"
    publish = helper.publish_directory
    target = tmp_path / "alias target"

    def insert_and_publish(staged, final):
        assert verify_backup(staged).schema_version == 1 and not final.exists()
        if entry == "file":
            final.write_bytes(b"keep existing")
        elif entry == "directory":
            final.mkdir()
        else:
            target.mkdir()
            if os.name == "nt":
                subprocess.run(
                    ["cmd.exe", "/d", "/c", "mklink", "/J", str(final), str(target)],
                    check=True,
                    capture_output=True,
                )
            else:
                final.symlink_to(target, target_is_directory=True)
            target.rename(tmp_path / "moved target")
        return publish(staged, final)

    monkeypatch.setattr(helper, "publish_directory", insert_and_publish)
    with pytest.raises(FileExistsError):
        helper.backup(runtime, destination)
    if entry == "file":
        assert destination.read_bytes() == b"keep existing"
    elif entry == "directory":
        assert list(destination.iterdir()) == []
    else:
        destination.lstat()
        assert not target.exists()
    assert not list(tmp_path.glob(".docintel-staging-*"))


def test_two_helpers_race_for_one_final_snapshot(runtime, helper, tmp_path, monkeypatch):
    destination = tmp_path / "race"
    barrier = threading.Barrier(2, timeout=10)
    publish = helper.publish_directory

    def concurrent(staged, final):
        assert verify_backup(staged).schema_version == 1
        barrier.wait()
        return publish(staged, final)

    monkeypatch.setattr(helper, "publish_directory", concurrent)

    def attempt():
        try:
            helper.backup(runtime, destination)
            return "published"
        except FileExistsError:
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == ["published", "refused"]
    assert verify_backup(destination).schema_version == 1
    assert not list(tmp_path.glob(".docintel-staging-*"))
    if os.name == "posix":
        assert stat.S_IMODE(destination.stat().st_mode) == 0o700
        for _, path in verify_backup(destination).entries:
            assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_cleanup_failure_preserves_original_error_and_only_owned_staging(
    runtime, helper, tmp_path, monkeypatch, caplog
):
    destination = tmp_path / "final"
    unrelated = tmp_path / ".docintel-staging-unrelated"
    unrelated.mkdir()
    (unrelated / "keep").write_bytes(b"keep")
    root = OSError(errno.ENOSPC, "PRIVATE_CANARY root")
    monkeypatch.setattr(helper, "sync_files", lambda _: (_ for _ in ()).throw(root))
    remove = publication.shutil.rmtree

    def cleanup(path, *a, **kw):
        if Path(path).name.startswith(".docintel-staging-"):
            raise PermissionError("PRIVATE_CANARY cleanup")
        return remove(path, *a, **kw)

    monkeypatch.setattr(publication.shutil, "rmtree", cleanup)
    with pytest.raises(OSError) as failed:
        helper.backup(runtime, destination)
    assert failed.value is root and not destination.exists()
    assert (unrelated / "keep").read_bytes() == b"keep"
    assert len(list(tmp_path.glob(".docintel-staging-*"))) == 2
    assert "staging retained" in caplog.text and "PRIVATE_CANARY" not in caplog.text


def test_empty_schema2_backup_does_not_create_source_assets_directory(helper, tmp_path):
    source = tmp_path / "empty"
    DocumentRepository(source / "documents.sqlite3").initialize()
    before = tree(source)
    helper.backup(source, tmp_path / "snapshot")
    assert tree(source) == before and not (source / "documents").exists()
    assert verify_backup(tmp_path / "snapshot").schema_version == 2


def test_backup_destination_inside_source_is_rejected_before_staging(runtime, helper):
    before = tree(runtime)
    with pytest.raises(ValueError, match="outside"):
        helper.backup(runtime, runtime / "nested" / "snapshot")
    assert tree(runtime) == before and not (runtime / "nested").exists()


def test_unsupported_publication_fails_without_overwrite(tmp_path, monkeypatch):
    if os.name == "nt":
        # Test the native error path through a real existing Windows destination.
        source, destination = tmp_path / "source", tmp_path / "target"
        source.mkdir()
        destination.mkdir()
        with pytest.raises(FileExistsError):
            publication.publish_directory(source, destination)
    else:
        monkeypatch.setattr(publication.sys, "platform", "unsupported-test-os")
        with pytest.raises(OSError) as failure:
            publication.publish_directory(tmp_path / "source", tmp_path / "target")
        assert failure.value.errno == errno.ENOTSUP
    assert not (tmp_path / "target" / "documents.sqlite3").exists()


def test_backup_includes_committed_wal_data_without_ignoring_it(runtime, helper, tmp_path):
    with closing(sqlite3.connect(runtime / "documents.sqlite3")) as source:
        source.execute("PRAGMA journal_mode=WAL")
        source.execute("UPDATE documents SET filename='committed-in-wal.png'")
        source.commit()
        assert (runtime / "documents.sqlite3-wal").is_file()
        helper.backup(runtime, tmp_path / "wal-snapshot")
        with closing(
            sqlite3.connect(
                (tmp_path / "wal-snapshot/documents.sqlite3").as_uri() + "?mode=ro&immutable=1",
                uri=True,
            )
        ) as snapshot:
            assert snapshot.execute("SELECT filename FROM documents").fetchone() == (
                "committed-in-wal.png",
            )
    assert verify_backup(tmp_path / "wal-snapshot").schema_version == 1


def test_runtime_journal_is_not_ignored_or_repaired(runtime, helper, tmp_path):
    (runtime / "documents.sqlite3-journal").write_bytes(b"synthetic pending journal")
    before = tree(runtime)
    with pytest.raises(ValueError, match="recovery"):
        helper.backup(runtime, tmp_path / "snapshot")
    assert not (tmp_path / "snapshot").exists() and tree(runtime) == before
    assert not list(tmp_path.glob(".docintel-staging-*"))


def test_lost_publish_ack_keeps_verified_final_backup(runtime, helper, tmp_path, monkeypatch):
    publish = helper.publish_directory
    destination = tmp_path / "snapshot"

    def lost_ack(source, target):
        publish(source, target)
        raise OSError("synthetic lost publication acknowledgement")

    monkeypatch.setattr(helper, "publish_directory", lost_ack)
    with pytest.raises(OSError):
        helper.backup(runtime, destination)
    assert verify_backup(destination).schema_version == 1
    assert not list(tmp_path.glob(".docintel-staging-*"))
