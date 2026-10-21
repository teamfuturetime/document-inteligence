from pathlib import Path

import pytest

from app.services.storage import LocalStorage


def test_save_uses_basename_and_delete_removes_file(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)

    stored = storage.save("../unsafe/scan.png", b"image")

    assert stored.original_name == "scan.png"
    assert stored.path.parent == tmp_path
    assert stored.path.read_bytes() == b"image"

    storage.delete(stored.stored_name)
    assert not stored.path.exists()


def test_delete_rejects_path_outside_storage(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)

    with pytest.raises(ValueError, match="Invalid storage path"):
        storage.delete("../outside.pdf")
