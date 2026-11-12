# Phát triển local

Lệnh cài/chạy/check chỉ duy trì ở [README gốc](../../README.md) và `scripts/dev.py`. Nền chính: docintel + SQLite worker; không còn chỉ foundation, DB/uploads/reviews đã có. Cấu hình mẫu chọn tesseract, không phải fixture. Backend mặc định unconfigured khi không có `.env`; setup chỉ tạo file nếu chưa có, không ghi đè secret.

Runtime models/DB/uploads/reports ở `runtime/` ignored. Một app/worker mỗi DB. [Runbook](../product/runbook.md) có demo/backup/restart; [verification](../consolidation-verification.md) ghi môi trường đã chạy và phần chưa xác minh. Docker optional, không suy từ YAML. Windows dùng `python`, macOS/Linux có thể cần `python3`; uv chọn Python backend theo pin.
