# Document Intelligence cho biểu mẫu tiếng Việt

**Mã đề tài:** AI-02
**Nhóm:** SE2026-T11 – Future Time
**Thành viên:** Nguyễn Minh Thao (MSSV: 23001936) – Thành viên phát triển
**Nhánh triển khai cá nhân:** `minhthao`

## Giới thiệu

Hệ thống Document Intelligence ứng dụng AI để tự động xử lý, nhận diện và trích xuất thông tin từ biểu mẫu tiếng Việt. Hệ thống tiếp nhận PDF, JPG, JPEG, PNG; tiền xử lý ảnh; nhận diện văn bản tiếng Việt bằng OCR; phân loại biểu mẫu; trích xuất thông tin quan trọng thành JSON có cấu trúc; cho phép người dùng xem, chỉnh sửa và xác nhận kết quả; lưu trữ và tìm kiếm tài liệu qua giao diện thân thiện.

## Luồng xử lý

```
Người dùng → React → FastAPI → Upload → Tiền xử lý → OCR → Phân tích bố cục
→ AI Document Understanding → JSON → Chuẩn hóa → Người dùng xác nhận
→ PostgreSQL + File Storage
```

## Công nghệ

| Tầng | Công nghệ |
|------|-----------|
| Frontend | React, TypeScript, Tailwind CSS, Axios, React Router |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| AI/OCR | PaddleOCR, OpenCV, PyMuPDF, mô hình phân tích bố cục, LLM/Document Understanding, JSON Schema |
| Dữ liệu & triển khai | PostgreSQL, MinIO/file storage, Docker, Docker Compose, Git/GitHub |
| Kiểm thử | Pytest, FastAPI TestClient, integration tests, end-to-end tests |

## Cấu trúc thư mục

```
document-intelligence-vietnamese/
  frontend/src/{components,pages,services,hooks,types}/
  frontend/package.json
  backend/app/{api,core,models,schemas,services,repositories}/
  backend/app/main.py
  backend/migrations/
  backend/requirements.txt
  ai_service/{ocr,preprocessing,classification,extraction,evaluation}/
  ai_service/main.py
  tests/{unit,integration,e2e}/
  docs/{architecture,database,pipeline,api,evaluation}.md
  scripts/
  docker-compose.yml
  .env.example
  .gitignore
  README.md
```

## Bắt đầu nhanh

Xem hướng dẫn chi tiết trong [docs/architecture.md](docs/architecture.md) và [docs/pipeline.md](docs/pipeline.md).

```bash
# 1. Sao chép cấu hình môi trường
cp .env.example .env

# 2. Khởi động toàn bộ hệ thống bằng Docker Compose
docker compose up --build

# 3. Truy cập
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/docs
```

## Tài liệu

- [Kiến trúc hệ thống](docs/architecture.md)
- [Thiết kế cơ sở dữ liệu](docs/database.md)
- [Pipeline xử lý tài liệu](docs/pipeline.md)
- [Tài liệu API](docs/api.md)
- [Đánh giá AI](docs/evaluation.md)

## Quy ước commit

- Mỗi task tương ứng tối thiểu 1 commit riêng, có thay đổi thực chất và có thể kiểm chứng.
- Commit message theo chuẩn Conventional Commits: `feat`, `fix`, `docs`, `test`, `chore`, `perf`.
- Không push trực tiếp lên `main`; mọi commit triển khai cá nhân thực hiện trên nhánh cá nhân và tích hợp qua Pull Request.

