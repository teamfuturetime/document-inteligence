import pytest

from docintel.storage.local import LocalDocumentStorage


@pytest.mark.parametrize(
    "identifier",
    [
        "../outside",
        r"C:\temp\file",
        r"folder\file",
        "/tmp/file",
        "a/../b",
        "A" * 32,
        "a" * 31,
        "a" * 33,
    ],
)
def test_storage_id_namespace_rejects_paths_on_every_platform(tmp_path, identifier):
    storage = LocalDocumentStorage(tmp_path / "storage")
    with pytest.raises(ValueError):
        storage.path(identifier, "source")


@pytest.mark.parametrize("inside", [False, True])
def test_symlinks_are_rejected_even_when_target_stays_inside_storage(tmp_path, inside):
    storage = LocalDocumentStorage(tmp_path / "storage")
    target = storage.root / "target" if inside else tmp_path / "outside"
    target.write_bytes(b"private")
    link = storage.root / ("a" * 32 + ".source")
    link.symlink_to(target)
    with pytest.raises(ValueError):
        storage.path("a" * 32, "source")
    assert target.read_bytes() == b"private"


def test_opaque_regular_file_roundtrip_still_works(tmp_path):
    storage = LocalDocumentStorage(tmp_path / "storage")
    storage.write("a" * 32, "source", b"synthetic")
    assert storage.path("a" * 32, "source").read_bytes() == b"synthetic"
    storage.discard("a" * 32)
    assert not storage.path("a" * 32, "source").exists()
