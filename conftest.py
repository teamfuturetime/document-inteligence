from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption("--run-ocr", action="store_true", help="Require and run the real OCR engine tests")
    parser.addoption("--tessdata-dir", default="data/models/tessdata", help="Pinned vie/eng model directory")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-ocr"):
        for item in items:
            if item.get_closest_marker("ocr_integration"):
                item.add_marker(pytest.mark.skip(reason="real OCR requires explicit --run-ocr"))


@pytest.fixture
def tessdata_dir(request):
    return Path(request.config.getoption("--tessdata-dir")).resolve()
