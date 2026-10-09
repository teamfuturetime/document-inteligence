# Vietnamese Document Intelligence — AI-02

Ứng dụng web phục vụ nhóm 5 người: upload hóa đơn tiếng Việt, OCR, trích xuất
dữ liệu có cấu trúc, review/chỉnh sửa, validation và xuất JSON.

## Trạng thái

Đã khởi tạo cấu trúc và tài liệu Phase 0. Chưa có ứng dụng chạy được,
API, OCR, mock extraction, dataset hoặc CI kiểm thử ứng dụng.
Các interface trong tài liệu là đề xuất để chốt ở Phase 1.

## Phạm vi MVP đề xuất

- Hóa đơn bán hàng tổng hợp dạng in; một tài liệu mỗi lần.
- PNG/JPG và PDF một trang; dữ liệu hoàn toàn synthetic.
- Trích xuất số hóa đơn, ngày, tên bên bán, tổng tiền và tiền tệ VND.
- Mỗi trường có giá trị, confidence và nguồn OCR; không tìm thấy thì trả null.
- Review trên trình duyệt, sửa giá trị, validation và tải JSON đã xác nhận.
- Golden dataset có ground truth, đánh giá từng trường, taxonomy lỗi,
  version cấu hình và hướng dẫn tái lập.

Chưa đưa vào MVP: chữ viết tay, bảng chi tiết sản phẩm, PDF nhiều trang,
biểu mẫu tùy ý, database, authentication, microservices và cloud.

## Bắt đầu

1. Đọc [kiến trúc và MVP](docs/architecture.md).
2. Đọc [roadmap](docs/roadmap.md) và [backlog issue](docs/issues.md).
3. Làm theo [quy trình Git và task đầu tiên](docs/contributing.md).

Không có lệnh chạy frontend/backend ở Phase 0. Hướng dẫn cài dependency,
chạy demo và test sẽ được bổ sung khi hoàn thành skeleton ở Phase 2.

## Cấu trúc

| Thư mục | Vai trò |
| --- | --- |
| `frontend/` | React + TypeScript + Vite; upload, preview, review, export |
| `backend/` | FastAPI, Pydantic; HTTP API, điều phối và validation |
| `pipeline/` | Python; preprocessing, adapter OCR và extraction độc lập |
| `schemas/` | JSON Schema/fixtures dùng chung, quản lý phiên bản contract |
| `evaluation/` | CLI evaluation, metrics và taxonomy lỗi |
| `data/` | Mẫu synthetic, ground truth, manifest và chia tập |
| `docs/` | Kiến trúc, kế hoạch và hướng dẫn cộng tác |
| `.github/` | Template issue và pull request |

Tests đặt trong `frontend/src/`, `backend/tests/`, `pipeline/tests/` và
`evaluation/tests/` khi triển khai. Không tạo package rỗng giả là code hoạt động.
