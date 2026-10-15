# AI pipeline

Owner: thành viên 4 — preprocessing/OCR; thành viên 5 — extraction.

Hai người làm trong module riêng. Package Python độc lập với FastAPI;
OCR và extraction thay thế qua interface. Backend và evaluation dùng lại cùng
package. P3-01 đã có preprocessing PNG/JPEG/PDF một trang trong subprocess:
decode, sửa hướng EXIF, nền trắng, grayscale và metadata tọa độ/config.
Tests nằm ở `tests/`, được chạy cùng pytest từ root workspace.

```bash
uv sync --locked
.venv/bin/python -m document_pipeline.preprocessing data/samples/synthetic-001.pdf --output /tmp/ai02-prepared/page.png
```

Lệnh chạy từ repository root. Xem [hướng dẫn preprocessing](../docs/preprocessing.md)
và [ranh giới module](../docs/architecture.md).

P3-02 đã có adapter Tesseract 5 `vie+eng`, model installer/hash verification,
OCRResult contract và CLI. Xem [hướng dẫn OCR](../docs/ocr.md) để cài model và
chạy engine thật. Extraction và nối pipeline thật vào API chưa triển khai;
web vẫn chạy fixed mock.
