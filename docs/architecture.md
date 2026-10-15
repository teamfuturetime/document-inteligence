# Kiến trúc hệ thống

## 1. Tổng quan

Hệ thống Document Intelligence cho biểu mẫu tiếng Việt được thiết kế theo kiến trúc **modular monolith** với 3 thành phần chính chạy độc lập trong Docker Compose:

```
┌─────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│    Frontend     │ ───▶ │     Backend      │ ───▶ │    AI Service    │
│  React + TS     │ HTTP │   FastAPI        │ HTTP │  OCR + AI        │
│  Tailwind CSS   │      │   SQLAlchemy     │      │  PaddleOCR/OpenCV│
└─────────────────┘      └────────┬─────────┘      └──────────────────┘
                                  │
                        ┌─────────▼─────────┐
                        │    PostgreSQL     │
                        │  + File Storage   │
                        └───────────────────┘
```

## 2. Các module

### 2.1 Frontend (`frontend/`)
- **React + TypeScript + Vite**: giao diện người dùng.
- **Tailwind CSS**: styling.
- **Axios**: gọi API backend.
- **React Router**: điều hướng giữa các trang (Upload, Review, History).
- Các thư mục: `components/`, `pages/`, `services/`, `hooks/`, `types/`.

### 2.2 Backend (`backend/`)
- **FastAPI**: REST API, tự động sinh OpenAPI docs.
- **Pydantic**: validation schema.
- **SQLAlchemy + Alembic**: ORM và migration.
- Các lớp:
  - `api/`: router FastAPI (documents, processing, review).
  - `core/`: config, database, logging, security.
  - `models/`: SQLAlchemy models.
  - `schemas/`: Pydantic schemas.
  - `services/`: business logic (upload, validation, processing, storage).
  - `repositories/`: truy vấn dữ liệu.

### 2.3 AI Service (`ai_service/`)
- **preprocessing/**: tiền xử lý ảnh (OpenCV), chuyển PDF sang ảnh (PyMuPDF), deskew.
- **ocr/**: nhận diện văn bản tiếng Việt (PaddleOCR), bounding boxes, chuẩn hóa Unicode.
- **classification/**: phân loại biểu mẫu.
- **extraction/**: trích xuất trường dữ liệu theo JSON Schema.
- **evaluation/**: đo CER, WER, Precision, Recall, F1.

### 2.4 Dữ liệu
- **PostgreSQL**: lưu metadata tài liệu, kết quả trích xuất, trạng thái xác nhận.
- **File Storage**: lưu file gốc và ảnh đã tiền xử lý (local storage hoặc MinIO).

## 3. Luồng dữ liệu

```
1. Người dùng upload file (PDF/JPG/JPEG/PNG) qua Frontend
2. Backend validate file (loại, kích thước) → lưu file → tạo Document record
3. Backend gọi AI Service:
   a. Tiền xử lý ảnh (deskew, tăng tương phản)
   b. OCR tiếng Việt → text + bounding boxes
   c. Phân loại biểu mẫu
   d. Trích xuất trường dữ liệu → JSON
4. Backend chuẩn hóa kết quả → lưu Extraction record
5. Người dùng xem, chỉnh sửa, xác nhận kết quả
6. Kết quả đã xác nhận được lưu vĩnh viễn, có thể tìm kiếm
```

## 4. Quyết định thiết kế

| Quyết định | Lý do |
|------------|-------|
| Tách AI Service thành service riêng | OCR/AI tốn CPU/RAM, cần scale độc lập; tránh chặn API chính |
| Repository pattern ở backend | Tách truy vấn DB khỏi business logic, dễ test |
| Pydantic schema ở mọi biên | Đảm bảo dữ liệu vào/ra có cấu trúc rõ ràng |
| JSON Schema cho trích xuất | Cho phép định nghĩa cấu trúc kết quả theo từng loại biểu mẫu |
| Fallback OCR khi không có PaddleOCR | MVP chạy được ngay cả khi chưa cài model nặng |

## 5. Ràng buộc biến thể RE-044

- Phục vụ tối đa **421 người dùng hoạt động đồng thời** (kiểm thử tải).
- Thời gian lưu giữ dữ liệu **41 ngày**, có script xóa dữ liệu hết hạn (`scripts/retention.py`).
- Quy trình phản hồi change request trong **18 giờ** (ghi nhận trong docs).
- Ưu tiên người dùng lần đầu; quản lý yêu cầu thay đổi sau prototype.
