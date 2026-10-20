# AI-02 — Document Intelligence cho biểu mẫu tiếng Việt

Ứng dụng dự kiến nhận tài liệu mẫu, OCR, trích xuất các trường theo schema,
cho phép người dùng kiểm tra/chỉnh sửa, validation ở backend và xuất JSON.
Chỉ dùng dữ liệu tổng hợp hoặc dữ liệu mẫu được phép sử dụng.

## Trạng thái thực tế

Ngày khảo sát: **20/10/2026**. Nhánh phát triển cá nhân: **`tuannguyen`**.

Giai đoạn 0 chỉ khảo sát repository và lập kế hoạch. Nhánh này hiện có tài liệu;
chưa có backend, frontend, OCR, VLM, bộ dữ liệu hay test ứng dụng.
Code trên các nhánh remote đã được đọc để tham khảo, chưa được nhập vào nhánh này.

## Tài liệu

- [Khảo sát repository và môi trường](docs/repository-audit.md).
- [Yêu cầu, phạm vi MVP và trạng thái 12 yêu cầu](docs/requirements.md).
- [Kiến trúc tối giản và luồng dữ liệu dự kiến](docs/architecture.md).
- [Roadmap, task nhỏ và điều kiện hoàn thành](docs/roadmap.md).

## Cài đặt, chạy và kiểm tra

Chưa có ứng dụng để cài đặt hoặc chạy. Giai đoạn 0 không cài dependency,
không gọi dịch vụ AI và không cần API key.

Có thể kiểm tra trạng thái repository bằng PowerShell tại thư mục gốc:

```powershell
git branch --show-current
git status --short --branch
git log -1 --oneline
git diff --check
```

Môi trường được phát hiện có Python 3.13.7, Node.js 24.13.0, npm 11.6.2,
Git 2.52.0.windows.1 và Tesseract 5.5.0.20241111 với `vie`/`eng`.
Đây là kết quả kiểm tra công cụ, chưa chứng minh ứng dụng hoặc dependency tương thích.
Hướng dẫn tạo môi trường, khóa dependency, chạy server và test sẽ được bổ sung
khi từng task trong Giai đoạn 1 được thực hiện và kiểm tra.

## Giới hạn và bước tiếp theo

Chưa chọn OCR/VLM provider, chưa đo chất lượng nhận dạng hay extraction.
Confidence sẽ chỉ hiển thị khi có nguồn và cách tính rõ ràng;
không xem confidence là bảo đảm dữ liệu đúng.

Task tiếp theo: **S1.1 — backend FastAPI và health-check**, có test chạy offline
và commit local riêng. Chỉ thực hiện sau lần khảo sát này; không triển khai toàn bộ
roadmap trong một lượt và không tự động push, tạo PR hoặc merge.
