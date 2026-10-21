# ADR 0001 — Tesseract local cho OCR MVP

- Ngày: 21/10/2026. Trạng thái: chấp nhận cho S3.2, dựa trên smoke test tổng hợp.
- Bối cảnh: cần OCR tiếng Việt thật, chạy offline; máy đã có Tesseract và `vie`.
  S3.1 là extraction contract/fake, chưa phải OCR hoặc VLM.
- Quyết định: gọi CLI Tesseract qua OCRProvider riêng; chọn OEM 1, PSM 6, `vie`,
  DPI 300. So sánh `vie` và `vie+eng` trên cùng mẫu cho thấy `vie` giữ dấu tốt hơn;
  chưa so sánh nhiều engine hoặc tối ưu trên golden dataset.
- Dùng Pillow để giải mã và áp dụng EXIF; giữ raw text/TSV, vị trí và native score.
  Model được định danh bằng hash; không phân phối model/executable và không tự tải.
- Hệ quả: không cần mạng/API key, thêm một dependency Python. Máy chạy tích hợp cần
  cài engine/model; unit test vẫn chạy riêng được. Có giới hạn về dấu tiếng Việt,
  guard ảnh và thời hạn từng tiến trình; chưa có SLA hoặc benchmark tổng quát.
- OCR chỉ tạo observations; không sửa S3.1/canonical schema, không thay thế VLM,
  không suy ra trường hóa đơn hoặc confidence extraction từ score OCR.

Phiên bản, model hash, nguồn/license, cách chạy và lỗi cụ thể ở [OCR local](../ocr.md).
