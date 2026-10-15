# Chạy demo và kiểm tra bàn giao

MVP local trên macOS/Linux: Python ≥ 3.11 + uv, Node theo engines frontend,
Tesseract 5. Máy hiện tại đã có vie/eng đã pin trong data/models/tessdata.

## Khởi động

Từ repository root trên `personal/canhtung-main`:

```bash
uv sync --locked
tesseract --version
.venv/bin/python -m document_pipeline.ocr_models --directory data/models/tessdata
.venv/bin/python -m uvicorn document_backend.main:app --host 127.0.0.1 --port 8000
```

Terminal khác:

```bash
cd frontend
npm ci
npm run dev
```

Mở http://127.0.0.1:5173/. Health ở http://127.0.0.1:8000/health cần báo
mode real/ocr_ready true; Swagger ở /docs. VDI_TESSDATA_DIR override model path.
Mock chỉ khi chọn rõ VDI_MODE=mock; real lỗi không fallback fixture.

## Kịch bản demo

1. Chọn data/samples/synthetic-001.png, xem preview, bấm **Trích xuất hóa đơn**.
2. Đối chiếu năm field với tài liệu, xem confidence/warnings/evidence.
3. Sửa tên bên bán; thử ngày 2026-02-30 để thấy lỗi field.
4. Sửa ngày về 2026-10-09, bấm **Kiểm tra dữ liệu**, rồi **Xuất JSON đã xác nhận**.
5. JSON giữ AI gốc, mode/version và edited_fields. Sửa tiếp field phải vô hiệu export.
6. Lặp với JPG/PDF; PDF native viewer có link tải dự phòng.
7. synthetic-002-missing.png cần reviewer nhập tiền tệ trước export.
8. File giả/đa trang/vượt giới hạn báo lỗi, không trả fixture thay thế.

## Tái chạy verification

```bash
.venv/bin/python -m backend.export_schemas --check
.venv/bin/python -m pytest --run-ocr --tessdata-dir=data/models/tessdata -q
.venv/bin/python -m document_evaluation.cli --tessdata-dir data/models/tessdata --split test --output evaluation/reports/test.json --check
cd frontend
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Playwright tự chạy/dừng backend 18000, Vite 15173; không reuse server đang mở.
Nếu port bận, kiểm tra tiến trình do mình tạo, không kill tiến trình không rõ.
Browser tests tải JSON thật và kiểm tra Pydantic ReviewedExport. Screenshots/
traces trong frontend/test-results được ignore. Local QA dùng
PLAYWRIGHT_BROWSERS_PATH=/private/tmp/ai02-playwright cho browser cache tạm.

## Troubleshooting và giới hạn

- Health OCR false/extract 503: kiểm tra Tesseract 5 và model installer --check.
- 415/422: kiểm tra bytes PNG/JPEG/PDF một trang, không mật khẩu, ≤10 MiB/25M pixel.
- 504: vượt 30 giây xử lý; process group được dừng, thử tài liệu đơn giản hơn.
- Validation lỗi: ngày ISO/calendar, tiền integer VND/safe range, đủ năm field.
- PDF không hiện: tải bản gốc để đối chiếu; viewer phụ thuộc trình duyệt.
- OCR mất dấu/layout khó: review trước export; confidence chưa hiệu chuẩn,
  baseline chưa hỗ trợ bảng/nhiều cột/nhãn khác dòng.

Không cloud/database/auth, không tài liệu cá nhân thật. Xem [completion](completion.md)
và [evaluation](evaluation.md) cho evidence và phần cần review nhóm.
