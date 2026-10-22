# API

Base URL backend: `/api/v1`. Swagger: `/docs`.

| Method | Path | Thành công | Mô tả |
|---|---|---:|---|
| POST | `/documents` | 201 | Multipart field `file`; PDF/JPEG/PNG, mặc định ≤10 MB |
| GET | `/documents` | 200 | `page`, `page_size`, `status`, `search`, `document_type` |
| GET | `/documents/{id}` | 200 | Metadata tài liệu |
| POST | `/documents/{id}/process` | 200 | Gửi file nội bộ tới AI service và lưu extraction |
| GET | `/documents/{id}/extraction` | 200 | Kết quả trích xuất |
| PATCH | `/documents/{id}/extraction` | 200 | Body `{data, document_type?}`; đánh dấu reviewed |
| POST | `/documents/{id}/confirm` | 200 | Xác nhận kết quả đã rà soát |
| DELETE | `/documents/{id}` | 200 | Xóa record và file tương ứng |

Mã lỗi chính: `400` file sai định dạng, `413` quá dung lượng, `404` không tồn tại,
`422` body không hợp lệ, `502` AI service thất bại, `500` lỗi không dự kiến.

AI service:

| Method | Path | Mô tả |
|---|---|---|
| GET | `/health` | Engine cấu hình và engine runtime khả dụng |
| POST | `/process` | Multipart `file`, trả `ocr`, `classification`, `extraction` |

`classification.confidence` thuộc [0,100], loại `heuristic`; không được diễn giải
như xác suất. `matched_rules` giải thích tín hiệu, `needs_review` yêu cầu kiểm tra tay.

## Cảnh báo bảo mật

Phiên bản này chưa xác thực người dùng và chưa phân quyền theo document. Không dùng
API trên Internet hoặc với dữ liệu cá nhân thật trước khi bổ sung authz, TLS, audit
và chính sách request-size ở reverse proxy.
