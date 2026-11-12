# AI pipeline

Package `document-pipeline` xử lý ảnh PNG/JPG một trang, OCR Tesseract 5 vie+eng, ánh xạ theo nhãn/vị trí dòng, normalization và field confidence heuristic. Không import FastAPI, database, frontend hoặc gold labels.

```powershell
uv sync --project backend --locked
uv run --project backend --locked python scripts/fetch_ocr_models.py
uv run --project backend --locked document-infer data/product/images/hoa_don_007.png --document-type hoa_don --tessdata-dir runtime/models/tessdata_fast --output runtime/inference/example.json
```

Truyền `--executable` nếu Tesseract không có trên PATH. Output phải là file mới; không ghi đè một run cũ. Có thể dùng `--config` với JSON hợp lệ theo `PipelineConfig`; runtime config và hash được giữ trong metadata. Application backend tự tìm PATH hoặc vị trí Tesseract Windows chuẩn; CLI mặc định dùng PATH.

- `config.py`: giới hạn và cấu hình được validate, version/hash.
- `preprocessing.py`, `image_worker.py`: worker giải mã ảnh có deadline, EXIF, nền alpha trắng, grayscale, rotation/scale có mapping về ảnh nguồn.
- `tesseract.py`: model checksums, native process có timeout, parser TSV và geometry.
- `extraction.py`, `normalization.py`: aliases trong resources, nhiều ứng viên mâu thuẫn thì abstain, giữ raw/normalized/evidence riêng.
- `service.py`: một entry point cho backend và benchmark; chỉ nhận bytes cùng document type.
- `provenance.py`: source hash, Git commit/dirty khi có, runtime và CPU.
- `tests/`: các ca geometry, malformed output, timeout, null/ambiguity và exact normalization.

Models ở runtime ngoài Git; không tải lúc inference, không fallback sang fixture, không suy currency từ ngôn ngữ. Confidence không phải xác suất đúng. [Nguồn kế thừa](../docs/ml/source-lineage.md), [kiến trúc](../docs/product/architecture.md).
