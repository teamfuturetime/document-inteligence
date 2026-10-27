from pathlib import Path

import pytest

from app.services.storage import LocalStorage


@pytest.mark.parametrize("filename", ["../unsafe/scan.png", r"C:\unsafe\scan.png"])
def test_save_uses_basename_and_delete_removes_file(tmp_path: Path, filename: str) -> None:
    storage = LocalStorage(tmp_path)

    stored = storage.save(filename, b"image")

    assert stored.original_name == "scan.png"
    assert stored.path.parent == tmp_path
    assert stored.path.read_bytes() == b"image"

    storage.delete(stored.stored_name)
    assert not stored.path.exists()


def test_same_original_name_gets_unique_storage_paths(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)

    first = storage.save("scan.png", b"first")
    second = storage.save("scan.png", b"second")

    assert first.stored_name != second.stored_name
    assert first.path.read_bytes() == b"first"
    assert second.path.read_bytes() == b"second"
    assert len(list(tmp_path.iterdir())) == 2


@pytest.mark.parametrize("operation", ["write", "rename"])
def test_failed_save_removes_temporary_file(tmp_path: Path, monkeypatch, operation: str) -> None:
    storage = LocalStorage(tmp_path)

    if operation == "write":
        original_write = Path.write_bytes

        def fail_write(path, content):
            original_write(path, content[:2])
            raise OSError("disk full")

        monkeypatch.setattr(Path, "write_bytes", fail_write)
    else:
        def fail_replace(*args):
            raise OSError("rename failed")

        monkeypatch.setattr("app.services.storage.os.replace", fail_replace)

    with pytest.raises(OSError):
        storage.save("scan.png", b"image")

    assert list(tmp_path.iterdir()) == []


def test_delete_rejects_path_outside_storage(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)

    with pytest.raises(ValueError, match="Invalid storage path"):
        storage.delete("../outside.pdf")
