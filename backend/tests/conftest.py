"""Real OCR is optional for ordinary offline tests and mandatory with an explicit flag."""


def pytest_addoption(parser):
    parser.addoption("--require-real-ocr", action="store_true", help="Fail instead of skip if real OCR is unavailable")
    parser.addoption("--ocr-tessdata-dir", default=None, help="Directory containing vie.traineddata")
    parser.addoption("--ocr-executable", default="tesseract", help="Local Tesseract executable")
