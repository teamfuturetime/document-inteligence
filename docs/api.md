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
| GET | `/documents/{id}` | Metadata không chứa storage path |
| GET | `/documents/{id}/preview` | PDF/ảnh inline, riêng tư |
| GET | `/documents/{id}/export` | JSON extraction an toàn |
| POST | `/documents/{id}/process` | OCR, phân loại, trích xuất và lưu |
| GET | `/documents/{id}/extraction` | Kết quả trích xuất |
| PATCH | `/documents/{id}/extraction` | Lưu chỉnh sửa `{data, document_type?}` |
| POST | `/documents/{id}/confirm` | Xác nhận kết quả |
| DELETE | `/documents/{id}` | Xóa record và file |

Mã lỗi chính: `400` file sai; `401` chưa đăng nhập; `403` CSRF sai; `404` không tồn tại/không sở hữu; `409` trạng thái không hợp lệ; `413` quá dung lượng; `422` body sai; `502` AI Service lỗi.

AI Service có `GET /health` và `POST /process`. `classification.confidence` là heuristic 0–100, không phải xác suất hiệu chuẩn; backend lưu `matched_rules`, `confidence_type`, `needs_review` để giải thích.
