# Chạy local

[README](../../README.md) là nguồn lệnh setup/dev/checks. Kiểm chứng native Windows PowerShell với Python3.14.5/uv0.12.22/Node24.16.0/npm11.13.0; lệnh uv/npm tương thích cấu trúc cross-platform nhưng Linux/macOS/WSL2 và container chưa chạy trực tiếp.

Settings đọc `.env` ở root và env prefix DOCINTEL_; default unconfigured. Copy `.env.example` explicit fixture; thay env phải restart backend. Config JSON foundation là evaluator/generator riêng, không tự bật app. Backend8000/frontend5173 chỉ loopback; Vite proxy /api; Compose Nginx proxy tới backend qua mạng nội bộ. Không CORS wildcard/frontend key.

Dependencies: `uv sync --project backend --locked` và `npm --prefix frontend ci`. Cập nhật có chủ ý bằng uv/npm tool, regenerate locks/contract/evidence khi ảnh hưởng; không viết lock giả. Python native có thể default console cp1252; scripts success dùng ASCII, dữ liệu UTF-8; khi debug Unicode dùng `python -X utf8` hoặc biến PYTHONUTF8=1 trong terminal.

MVP persistence sẽ dùng runtime/ và backend/migrations khi BL-005 có runner/test thật; hiện không DB/upload/cache workflow. Dockerfiles/compose có pins và loopback, **không xác minh build/run** do Docker CLI chưa có. Khi có Docker: `docker compose config`, `docker compose up --build`, health + UI, rồi `docker compose down`; ghi kết quả thực, không tự cài Docker hoặc deploy cloud.
