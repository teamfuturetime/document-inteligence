# Onboarding

Trước khi nhận task, đọc [hướng dẫn nhận việc qua GitHub](github-collaboration.md): dùng tài khoản cá nhân, xác nhận trên issue, tạo nhánh theo task và review chéo. Phân công hiện hành nằm trên [issue #15](https://github.com/teamfuturetime/document-inteligence/issues/15); xem [vai trò và handles](roles.md).

1. Bắt đầu duy nhất tại [README gốc](../../README.md): cập nhật main, kiểm runtime pins, setup, models và hai server. Nền đã tích hợp qua PR #3; không chạy nhầm implementation của nhánh bài tập.
2. Chạy `python scripts/dev.py check`, `ocr`, `e2e` theo điều kiện trong README. Không gọi fixture replay là OCR thật.
3. Đọc [contracts](../../contracts/README.md), [kiến trúc](../product/architecture.md) và [CONTRIBUTING](../../CONTRIBUTING.md).
4. Chọn task trong Issues, comment nhận việc, kiểm dependency rồi tạo nhánh ngắn từ main mới nhất. Không phát triển tiếp trên nhánh cá nhân dài hạn như quy trình mặc định.
5. Đọc [inventory](../branch-inventory.md) trước khi port; giữ lineage, review contract/null/revision và kiểm bằng dữ liệu synthetic.
