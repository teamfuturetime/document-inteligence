# Extraction

Foundation có Protocol OCRAdapter image → OCRResult và ExtractionAdapter document_id/OCRResult → ExtractionRun, cùng fixture adapters. Thay engine bằng implementation Protocol, giữ spans/metadata/errors, thêm provider mode explicit/factory trong service/Settings, cập nhật capabilities/tests/benchmark. Không fallback fixture khi lỗi, không tìm đáp án model thật theo filename/ID.

BL-002 spike Tesseract/PaddleOCR trên mẫu Việt nhỏ: dấu/chữ/số/layout, runtime, weights/license/resources. BL-003 lưu spans/raw OCR scores/page/coordinates/image transforms; package version khác model weights hash/revision. Chưa tải engine/model hoặc kết luận engine nào tốt hơn.

BL-004 baseline nhãn/alias + vị trí, ghép dòng, format/candidates/abstain khi mơ hồ; không bỏ evidence hoặc điền thông tin không nguồn. OCR đúng không bảo đảm mapping đúng; benchmark predictions trước review và taxonomy để phân nguyên nhân.

BL-011 chỉ thử VLM nếu có hypothesis cải thiện từ baseline và policy/budget/quyền phù hợp. Adapter có ID/snapshot/prompt hash/version, timeout/retry/quota; parse/schema/validation output. OCR/ảnh là dữ liệu, không chỉ thị đổi schema/gọi tool. Thiếu thông tin abstain, không đọc gold; giữ baseline so sánh. API không pin snapshot phải báo hạn chế tái lập.

Nguồn tham khảo, không evidence đã chạy: [Tesseract data](https://tesseract-ocr.github.io/tessdoc/Data-Files.html), [PaddleOCR pipeline](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html).
