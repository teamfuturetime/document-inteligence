from pathlib import Path

import pytest

from app.services.storage import StorageSecurityError, StorageService


def test_storage_round_trip_uses_opaque_key(tmp_path):
    storage = StorageService(str(tmp_path))
    key = storage.save("../../cccd.pdf", b"safe")
    assert Path(key).name == key
    assert storage.read(key) == b"safe"
    assert storage.delete(key)


@pytest.mark.parametrize("key", ["../secret", "folder/file.pdf", "/tmp/file", "C:\\temp\\file"])
def test_storage_rejects_traversal_and_absolute_paths(tmp_path, key):
    storage = StorageService(str(tmp_path))
    with pytest.raises(StorageSecurityError):
        storage.read(key)


def test_storage_rejects_symlink_escape(tmp_path):
    storage = StorageService(str(tmp_path / "uploads"))
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    link = storage.base_path / "link.pdf"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Môi trường không cho phép tạo symlink")
    with pytest.raises(StorageSecurityError):
        storage.read("link.pdf")
