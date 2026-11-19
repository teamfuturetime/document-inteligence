# Hướng dẫn lỗi OCR — Refs #49

Workspace dùng lời nhắc cố định, không đưa raw error code/native stderr/đường dẫn vào alert.
`OcrErrorGuidance` nhận mã từ run đã lưu hoặc lỗi HTTP của thao tác chạy lại. Request ID
được hiển thị khi có và đúng định dạng token; history hiện không có request ID trong contract.
Không đổi domain/schema/generated types.

| Mã thực tế | Hướng xử lý |
| --- | --- |
| PROVIDER_UNAVAILABLE | Nhờ quản lý kiểm Tesseract/model vie+eng trước khi chạy lại |
| MODEL_HASH_MISMATCH | Kiểm checksum/cài model đúng pin |
| INPUT_CHANGED | Kiểm ảnh gốc; chạy lại không sửa checksum; tự upload thành tài liệu mới nếu cần |
| PROCESSING_INTERRUPTED | Chờ ứng dụng ổn định, chủ động chạy lại |
| PROCESSING_TIMEOUT | Ảnh rõ/gọn hơn, kiểm tài nguyên nếu lặp lại |
| INVALID_OCR_OUTPUT / PROVIDER_FAILED | Chủ động chạy lại; lỗi lặp lại cần kiểm engine/model |
| INVALID_DOCUMENT / FILE_TOO_LARGE / IMAGE_TOO_LARGE | Tự chọn ảnh hợp lệ, nhỏ hơn theo giới hạn |
| UNSUPPORTED_SCHEMA | Chọn loại tài liệu được hỗ trợ |
| PROCESSING_FAILED / unknown | Giữ bản nháp, nhờ quản lý kiểm tra; không hiển thị nội dung lỗi tùy ý |

Nguồn khảo sát: pipeline/src/document_pipeline/{tesseract,service,preprocessing}.py và
backend/src/docintel/services/documents.py (input checksum, interrupted recovery, fallback).
Lỗi receive/upload riêng giữ luồng hiện có; không mở rộng readiness/reconnect #50 hay recovery focus #51.

Nút Chạy OCR lại giữ guards busy/dirty/processing/is_latest_run/ocr_ready và gửi
expected_run_id hiện hành. Không tự upload, discard draft hoặc retry write. ReviewPanel,
session boundary, explicit null, revision/status CAS và owner enforcement giữ nguyên.
Chạy lại là tạo run mới; review cũ vẫn thuộc run cũ trong history, không tự sao chép sang run mới.

Kiểm tra: frontend contracts/typecheck/lint/format/test/build; backend generator --check.
Component tests kiểm known/unknown/prototype names, safe request ID, alert và explicit CAS retry.
Browser Chromium kiểm Enter trên retry, không POST trước khi người dùng chọn, và processed/review
với explicit null. HTTP/inference là doubles synthetic, không phải bằng chứng native OCR.
Browser spec tự chạy trong CI E2E hiện có; có thể chạy riêng bằng
`cd frontend` rồi `npx playwright test --config playwright.errors.config.ts` (chỉ cần Vite/Chromium).
