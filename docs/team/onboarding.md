# Onboarding

1. Bắt đầu duy nhất tại [README gốc](../../README.md): kiểm nhánh/nền, runtime pins, setup, models và hai server. Main GitHub hiện đang chờ PR nền; không chạy nhầm implementation của bài tập.
2. Chạy `python scripts/dev.py check`, `ocr`, `e2e` theo điều kiện trong README. Không gọi fixture replay là OCR thật.
3. Đọc [contracts](../../contracts/README.md), [kiến trúc](../product/architecture.md) và [CONTRIBUTING](../../CONTRIBUTING.md).
4. Chọn task tại backlog consolidation, tạo nhánh ngắn từ main sau khi nền được merge, hoặc từ consolidation trong lúc chờ và ghi rõ base PR. Không phát triển tiếp trên nhánh cá nhân dài hạn như quy trình mặc định.
5. Đọc [inventory](../branch-inventory.md) trước khi port; giữ lineage, review contract/null/revision và kiểm bằng dữ liệu synthetic.
