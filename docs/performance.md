# Hiệu năng và tải RE-044

Mục tiêu thiết kế là 421 người dùng hoạt động đồng thời. API chạy stateless với
2 worker/container, PostgreSQL connection health check và volume lưu file. OCR là
công việc CPU/GPU nặng; production nên chuyển `process` sang queue worker và trả
job ID thay vì giữ HTTP request.

## Kịch bản đo

Ramp từ 1 lên 421 virtual users trong 5 phút, giữ tải 15 phút. Tỉ lệ hành vi:
60% xem danh sách/detail, 25% upload, 10% xem extraction, 5% process. Theo dõi
p50/p95/p99, error rate, CPU, RAM, DB connections và queue depth. Tiêu chí đề
xuất: API đọc p95 < 500 ms, upload p95 < 2 s (không tính OCR), lỗi < 1%.

Các con số trên là tiêu chí, chưa phải kết quả đo. Cần môi trường staging, dataset
không chứa PII thật và công cụ như k6 để tạo báo cáo thực nghiệm.

## Phục hồi

Healthcheck ngăn frontend khởi động trước API/DB. Pipeline lưu trạng thái `failed`
và cho phép retry. PostgreSQL/file volume phải được backup, mã hóa và kiểm thử
restore định kỳ.
