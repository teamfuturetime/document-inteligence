# REST API

Base URL: `/api/v1`

| Method | Path | Mô tả |
|---|---|---|
| POST | `/documents` | Upload PDF/PNG/JPEG multipart field `file` |
| GET | `/documents` | Tìm kiếm, lọc, phân trang |
| GET | `/documents/{id}` | Metadata tài liệu |
| POST | `/documents/{id}/process` | Chạy pipeline |
| GET | `/documents/{id}/extraction` | JSON extraction mới nhất |

OpenAPI tương tác có tại `/docs`. Lỗi dùng cấu trúc FastAPI `{ "detail": ... }`.
