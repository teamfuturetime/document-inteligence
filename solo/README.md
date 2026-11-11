# AI-02 Solo — bản triển khai cá nhân

Ứng dụng độc lập do Cảnh Tùng quản lý, phát triển với trợ giúp AI. Nhánh
`personal/canhtung-solo` giữ lịch sử repository; mã mới nằm hoàn toàn trong
`solo/`, không import backend, pipeline hoặc giao diện của bản tích hợp cũ.
Đây là phiên bản ứng dụng cá nhân, không phải mô hình nền tự huấn luyện.

Phạm vi: hóa đơn bán hàng và đơn đề nghị sinh viên **synthetic** một trang,
PNG/JPEG/PDF; OCR → extraction theo schema → rà soát/sửa → validation → JSON.
So sánh OCR + luật, VLM và hybrid; báo cáo trạng thái thật của từng chế độ.

Xem [thiết kế và các checkpoint](docs/design.md). Hướng dẫn chạy và kết quả
kiểm thử được bổ sung cùng từng chức năng, không coi roadmap là tính năng đã có.
