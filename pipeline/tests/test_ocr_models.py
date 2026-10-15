import hashlib
import io

import pytest

from document_pipeline import ocr_models
from document_pipeline.ocr_models import ModelError, install_models, verify_models


@pytest.fixture
def models(monkeypatch):
    data = b"synthetic-test-model-not-real-traineddata"
    lock = {"revision": "test-revision", "models": {"vie": hashlib.sha256(data).hexdigest()}}
    monkeypatch.setattr(ocr_models, "MODEL_LOCK", lock)
    return data


def test_installer_verifies_pinned_download_and_reuses_cache(models, monkeypatch, tmp_path):
    urls = []
    def fetch(url, **kwargs):
        urls.append(url)
        return io.BytesIO(models)
    monkeypatch.setattr(ocr_models, "urlopen", fetch)
    install_models(tmp_path)
    assert verify_models(tmp_path) == {"vie": hashlib.sha256(models).hexdigest()}
    install_models(tmp_path)
    assert len(urls) == 1
    assert urls[0] == "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/test-revision/vie.traineddata"
    assert list(tmp_path.iterdir()) == [tmp_path / "vie.traineddata"]


def test_hash_mismatch_never_publishes_download_and_cleans_temp(models, monkeypatch, tmp_path):
    monkeypatch.setattr(ocr_models, "urlopen", lambda *args, **kwargs: io.BytesIO(b"corrupt"))
    with pytest.raises(ModelError):
        install_models(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_failed_download_preserves_existing_file(models, monkeypatch, tmp_path):
    destination = tmp_path / "vie.traineddata"
    destination.write_bytes(b"existing-corrupt")
    def fail(*args, **kwargs):
        raise OSError("synthetic download failure")
    monkeypatch.setattr(ocr_models, "urlopen", fail)
    with pytest.raises(ModelError):
        install_models(tmp_path)
    assert destination.read_bytes() == b"existing-corrupt"
    assert list(tmp_path.iterdir()) == [destination]


def test_verifier_rejects_corrupt_and_oversized_models(models, monkeypatch, tmp_path):
    path = tmp_path / "vie.traineddata"
    path.write_bytes(b"corrupt")
    with pytest.raises(ModelError):
        verify_models(tmp_path)
    path.write_bytes(models)
    monkeypatch.setattr(ocr_models, "MAX_MODEL_BYTES", 1)
    with pytest.raises(ModelError):
        verify_models(tmp_path)
