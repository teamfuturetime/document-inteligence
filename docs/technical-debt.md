# Sổ đăng ký nợ kỹ thuật

| ID | Mô tả | Thành phần | Mức độ | Tác động | Giải pháp đề xuất | Trạng thái |
|---|---|---|---|---|---|---|
| TD-01 | Chưa có authentication/authorization | Backend API | Critical | Ai biết ID có thể truy cập tài liệu | OIDC/JWT và kiểm tra ownership | Open |
| TD-02 | Chưa có frontend source | Frontend/Compose | Medium | Không có UI và image frontend không build được | Nhóm frontend cung cấp package/source thật | Open |
| TD-03 | Chưa có dataset gán nhãn | Classification | High | Không thể hiệu chuẩn confidence/đo accuracy | Dataset ẩn danh, split train/test, report metrics | Open |
| TD-04 | Chưa có integration/E2E container test | Tests | High | Rủi ro lỗi wiring PostgreSQL/OCR | Fixture tài liệu hợp pháp + CI Compose | Open |
| TD-05 | Filesystem và DB không atomic | Storage | Medium | Có thể còn orphan khi process chết giữa bước | Reconciliation job/outbox đơn giản | Accepted |
| TD-06 | Chưa scan malware/decompression bomb chuyên sâu | Upload | High | File độc hại có thể tốn tài nguyên | Sandbox OCR, antivirus, pixel/page limits | Open |
| TD-07 | Retention chưa có scheduler tích hợp | Operations | Medium | Dữ liệu hết hạn không tự xóa nếu không cấu hình cron | Cron/Task Scheduler gọi CLI và alert | Open |
| TD-08 | Paddle code là tùy chọn chưa được CI test | OCR | Low | Chọn `paddle` có thể lỗi dependency | Xóa code hoặc thêm image/profile và test riêng | Open |

Các mục Critical/High phải được xử lý trước production. Việc ghi nhận thay vì che
giấu giới hạn tuân theo quản lý technical debt của Lecture 05.
