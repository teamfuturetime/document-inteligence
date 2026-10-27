# API

Base URL: `/api/v1`; Swagger: `/docs`. Endpoint tài liệu yêu cầu cookie đăng nhập. Request ghi yêu cầu header `X-CSRF-Token` nhận từ đăng nhập/đăng ký.

| Method | Path | Mô tả |
|---|---|---|
| POST | `/auth/register` | Tạo người dùng và session |
| POST | `/auth/login` | Đăng nhập bằng email hoặc username |
| GET | `/auth/me` | Người dùng hiện tại |
| POST | `/auth/logout` | Hủy session |
| GET | `/documents/dashboard/summary` | Thống kê và tài liệu gần đây |
| POST | `/documents` | Upload PDF/JPEG/PNG ≤ 10 MB |
| GET | `/documents` | Phân trang; lọc `status`, `document_type`; `search` tên/OCR |
| GET | `/documents/{id}` | Metadata, raw/cleaned OCR và structured pages; không chứa storage path |
| GET | `/documents/{id}/preview` | PDF/ảnh inline, riêng tư |
| GET | `/documents/{id}/export` | JSON extraction an toàn |
| POST | `/documents/{id}/process` | OCR, phân loại, trích xuất và lưu |
| GET | `/documents/{id}/extraction` | Kết quả trích xuất |
| PATCH | `/documents/{id}/extraction` | Lưu chỉnh sửa `{data, document_type?}` |
| POST | `/documents/{id}/confirm` | Xác nhận kết quả |
| DELETE | `/documents/{id}` | Xóa record và file |

Mã lỗi chính: `400` file sai; `401` chưa đăng nhập; `403` CSRF sai; `404` không tồn tại/không sở hữu; `409` trạng thái không hợp lệ; `413` quá dung lượng; `422` body sai; `502` AI Service lỗi.

AI Service có `GET /health` và `POST /process`. `ocr.mean_confidence` là confidence
thật từ OCR engine; `classification.confidence` là heuristic 0–100, không phải xác
suất hiệu chuẩn. Backend lưu `matched_rules`, `confidence_type`, `needs_review` để
giải thích. Response OCR còn có `pages`, `boxes` và cấu hình Tesseract đã dùng.
# Rà soát bởi người dùng

- `PATCH /api/v1/documents/{id}/ocr-correction`: lưu bản OCR người dùng hiệu chỉnh; không ghi đè OCR máy.
- `PATCH /api/v1/documents/{id}/extraction`: tạo hoặc cập nhật trường thủ công và loại tài liệu đã duyệt.
- `POST /api/v1/documents/{id}/confirm`: xác nhận và khóa phiên rà soát.
- `POST /api/v1/documents/{id}/reopen`: mở lại tài liệu đã xác nhận trước khi sửa tiếp.
- `GET /api/v1/documents/{id}/export`: xuất giá trị hiệu lực đã duyệt cùng OCR gốc để kiểm toán.

Các endpoint thay đổi dữ liệu yêu cầu session hợp lệ, header CSRF và quyền sở hữu tài liệu.
