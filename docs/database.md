# Thiết kế cơ sở dữ liệu

## 1. ERD

```
┌─────────────────────┐       ┌──────────────────────┐
│      documents      │       │     extractions      │
├─────────────────────┤       ├──────────────────────┤
│ id (PK, UUID)       │ 1   1 │ id (PK, UUID)        │
│ filename            │◀──────│ document_id (FK)     │
│ content_type        │       │ document_type        │
│ file_size           │       │ data (JSONB)         │
│ file_path           │       │ confidence (Float)   │
│ status              │       │ status               │
│ ocr_text            │       │ created_at           │
│ ocr_boxes (JSONB)   │       │ updated_at           │
│ created_at          │       │ confirmed_at         │
│ updated_at          │       └──────────────────────┘
│ expires_at          │
└─────────────────────┘
```

## 2. Bảng `documents`

Lưu metadata của tài liệu đã upload.

| Cột | Kiểu | Ràng buộc | Mô tả |
|-----|------|-----------|-------|
| id | UUID | PK, default uuid4 | Khóa chính |
| filename | String(255) | NOT NULL | Tên file gốc |
| content_type | String(100) | NOT NULL | MIME type |
| file_size | Integer | NOT NULL | Kích thước (bytes) |
| file_path | String(500) | NOT NULL | Đường dẫn lưu trữ |
| status | String(20) | NOT NULL, default `uploaded` | Trạng thái xử lý |
| ocr_text | Text | NULL | Văn bản OCR đầy đủ |
| ocr_boxes | JSONB | NULL | Bounding boxes OCR |
| created_at | DateTime | NOT NULL, default now | Thời điểm tạo |
| updated_at | DateTime | NOT NULL, onupdate | Thời điểm cập nhật |
| expires_at | DateTime | NULL | Hết hạn lưu giữ (41 ngày) |

## 3. Bảng `extractions`

Lưu kết quả trích xuất JSON của từng tài liệu.

| Cột | Kiểu | Ràng buộc | Mô tả |
|-----|------|-----------|-------|
| id | UUID | PK, default uuid4 | Khóa chính |
| document_id | UUID | FK → documents.id, UNIQUE | Tài liệu tương ứng |
| document_type | String(50) | NOT NULL | Loại biểu mẫu |
| data | JSONB | NOT NULL | Dữ liệu trích xuất có cấu trúc |
| confidence | Float | NOT NULL, default 0 | Độ tin cậy trung bình |
| status | String(20) | NOT NULL, default `pending_review` | Trạng thái xác nhận |
| created_at | DateTime | NOT NULL, default now | Thời điểm tạo |
| updated_at | DateTime | NOT NULL, onupdate | Thời điểm cập nhật |
| confirmed_at | DateTime | NULL | Thời điểm người dùng xác nhận |

## 4. Index

- `documents.status` — lọc theo trạng thái.
- `documents.created_at` — sắp xếp theo thời gian.
- `documents.filename` — tìm kiếm theo tên (ILIKE).
- `extractions.document_id` — UNIQUE, truy vấn 1-1.
- `extractions.document_type` — lọc theo loại biểu mẫu.

## 5. Ràng buộc RE-044

- **Lưu giữ 41 ngày**: cột `expires_at = created_at + 41 ngày`; script `scripts/retention.py` xóa tài liệu hết hạn.
- **421 người dùng đồng thời**: pool kết nối PostgreSQL cấu hình phù hợp (pool_size, max_overflow).
