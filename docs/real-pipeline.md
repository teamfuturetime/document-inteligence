# API pipeline thật — P4-03

Backend mặc định `VDI_MODE=real`. Cài model theo [ocr.md](ocr.md), rồi chạy
Uvicorn từ root repository. `VDI_TESSDATA_DIR` tùy chọn chỉ thư mục model.
Mock chỉ được chọn rõ bằng `VDI_MODE=mock`; real không fallback mock khi lỗi.

`POST /api/v1/extract`: multipart một `file`, PNG/JPG/PDF một trang, tối đa
10 MiB/25M pixels. Full pipeline chạy trong process group POSIX riêng, deadline
30 giây tính từ khi bắt đầu xử lý. Timeout dừng cả worker/preprocessor/Tesseract
và thu hồi worker. Nhận body upload có deadline riêng 30 giây. Không lưu upload.
Pipeline dùng chung `run_document` với evaluation; hash config bao gồm
preprocessing, OCR và rules. Chỉ hỗ trợ macOS/Linux cho process-group cleanup.

`/health` báo mode thực, `ocr_ready` kiểm tra hash vie/eng và Tesseract 5.
Thiếu model/engine: extraction trả 503 `ocr_unavailable`; lỗi file 413/415/422,
timeout 504, lỗi nội bộ 500, không trả stderr/path. Validation hoạt động ở cả
hai mode theo [review-validation.md](review-validation.md).

Verification local: 111 backend tests pass khi bật real OCR, gồm HTTP upload
PNG/JPG/PDF → extraction → validation, error mapping và timeout worker thật.
Đây chưa phải GitHub CI hoặc browser E2E.
