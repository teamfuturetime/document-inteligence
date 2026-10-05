# AI-02 · Document Intelligence cho biểu mẫu tiếng Việt

Ứng dụng đích trích xuất trường dữ liệu từ hóa đơn/đơn từ mẫu, cho người dùng đối chiếu và sửa trước khi xuất JSON. Repository này mới hoàn thành **FOUNDATION 0.1.0**, chưa hoàn thành PRODUCT_MVP. Tài liệu và UI dùng tiếng Việt; định danh code dùng tiếng Anh.

| Phần | Tình trạng thực tế |
| --- | --- |
| FastAPI health/capabilities/schemas | Chạy thật; health không có nghĩa OCR sẵn sàng |
| Pydantic, JSON Schema/OpenAPI, TypeScript types | Sinh từ nguồn chuẩn backend, có kiểm tra drift |
| Chuẩn hóa và validation | Chạy thật: Unicode, chuỗi mã số, ngày tồn tại, ngày sinh/ngày đơn |
| UI giới thiệu và đối chiếu mẫu | Mẫu giả lập — chưa chạy OCR; chỉ xem |
| 6 ảnh và predictions synthetic | Fixture kiểm tra contract/UI; một số đáp án sai có chủ ý |
| Field-level evaluator | Chạy trên fixture; **chưa đo chất lượng mô hình** |
| Upload, OCR/extraction thật, persistence, sửa/lưu/xác nhận/export | Chưa triển khai; xem [backlog](docs/planning/backlog.md) |
| Docker, GitHub CI/ruleset | Có cấu hình local; tình trạng chạy trong [báo cáo](docs/reports/foundation-verification.md) |

Schema đơn đề nghị 7 trường, ảnh một trang và stack FastAPI + React là **PROVISIONAL**, áp dụng để dựng nền; chưa phải lựa chọn được nhóm duyệt cho sản phẩm cuối. Chỉ dùng synthetic/sample có nguồn và quyền phù hợp; không đưa hồ sơ thật, secret hay model weights vào Git.

## Chạy local

Môi trường đã kiểm tra: Windows PowerShell, Python **3.14.5**, uv **0.12.22**, Node **24.16.0**, npm **11.13.0**. Runtime được ghi tại `backend/.python-version`, `frontend/.node-version`; dependency được khóa bằng `backend/uv.lock` và `frontend/package-lock.json`. Không cần API key, GPU hoặc tải model.

Từ thư mục gốc, cài dependency và bật rõ chế độ mẫu:

```powershell
Copy-Item .env.example .env
uv sync --project backend --locked
npm --prefix frontend ci
```

Trên Linux/macOS dùng `cp .env.example .env` thay cho `Copy-Item`. Các lệnh uv/npm còn lại giống nhau; chưa được chạy trực tiếp trên hai hệ điều hành đó.

Terminal 1:

```powershell
uv run --project backend --locked uvicorn docintel.api.app:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
npm --prefix frontend run dev
```

Mở [giao diện](http://localhost:5173), chọn **Mẫu minh họa**. API docs tại [Swagger](http://127.0.0.1:8000/docs). Frontend proxy `/api` về backend. Nếu chưa có `.env`, provider mặc định `unconfigured`, catalogue trả `503 PROVIDER_UNAVAILABLE`; không tự chuyển sang fixture.

Docker (cần Docker Engine/Compose; **chưa chạy trên máy bàn giao**): sau khi tạo `.env`, dùng `docker compose up --build`; hai cổng chỉ bind loopback. `docker compose down` dừng ứng dụng. Không expose demo chưa có authentication ra Internet.

## Kiểm tra và sinh hợp đồng

```powershell
uv run --project backend --locked ruff check backend scripts
uv run --project backend --locked ruff format --check backend scripts
uv run --project backend --locked pytest backend/tests -q
uv run --project backend --locked python scripts/generate_contracts.py --check
uv run --project backend --locked python scripts/check_data.py
uv run --project backend --locked python scripts/evaluate_fixtures.py
uv run --project backend --locked python scripts/check_repository.py
npm --prefix frontend run contracts:check
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run format:check
npm --prefix frontend test
npm --prefix frontend run build
```

Có thể chạy toàn bộ checks bằng `uv run --project backend --locked python scripts/verify_foundation.py` (dừng frontend dev server trước vì script chạy `npm ci`; Windows khóa native DLL khi Vite đang dùng). Script fail ngay khi check lỗi, record ở runtime ngoài Git; không bao gồm Docker/CI remote/model benchmark.

Khi đổi domain/API: chạy `uv run --project backend --locked python scripts/generate_contracts.py`, sau đó `npm --prefix frontend run contracts:generate`; cập nhật fixtures/examples, version và tests liên quan. Khi cần sinh lại dữ liệu: `uv run --project backend --locked python scripts/generate_fixtures.py`, rồi `uv run --project backend --locked python scripts/generate_examples.py`; phải đối chiếu ảnh/gold, kiểm tra manifest và cập nhật evidence. Generator dùng font hệ thống, không phân phối font; khác font có thể khác checksum.

## Bắt đầu phát triển

Đọc [onboarding](docs/team/onboarding.md), [phạm vi](docs/requirements/scope.md), [contracts](contracts/README.md) và [CONTRIBUTING](CONTRIBUTING.md). [Danh mục tài liệu](docs/README.md) dẫn tới SRS, use cases, traceability, kiến trúc, ADR, dữ liệu, đánh giá và kế hoạch.

Bốn evidence môn học: golden dataset hiện mới có seed/format; metrics hiện kiểm tra evaluator; taxonomy có mã và ví dụ minh họa; versioning có contract/config và manifest lần chạy fixture. Không dùng các fixture này để khẳng định OCR/model có chất lượng. Xem [báo cáo bàn giao](docs/reports/foundation-verification.md) để biết lệnh đã chạy, hạn chế và năm việc tiếp theo.
