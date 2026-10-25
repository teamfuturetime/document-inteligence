# Phạm vi và nguồn yêu cầu

**Cập nhật 24/10/2026:** người dùng yêu cầu triển khai cả sản phẩm trên nhatquang. Phần foundation-only bên dưới là phạm vi lịch sử của lượt khởi tạo. Phạm vi mới ở [ADR 0007](../adr/0007-product-on-nhatquang.md), [kiến trúc](../product/architecture.md) và README; không phải xác nhận nhóm đã chọn nền chung hoặc thay rubric.

Nguồn giao việc: `AI02_CODEX_REPOSITORY_FOUNDATION.md`, phiên bản 1.0, ngày 05/10/2026, do người dùng cung cấp. Repository ban đầu chỉ có README và Git; giữ lịch sử, remote `teamfuturetime/document-inteligence`, nhánh `nhatquang` và không có thay đổi chưa commit. Không có AGENTS.md hiện hữu được tìm thấy trong repository/các thư mục cha đã kiểm tra.

## COURSE_REQUIRED — thông tin giảng viên đã cung cấp

| Mục | Nội dung gốc |
| --- | --- |
| Mã đề tài | AI-02 |
| Tên đề tài | Document Intelligence cho biểu mẫu tiếng Việt |
| Bài toán / mục tiêu | Trích xuất trường dữ liệu từ hóa đơn/đơn từ mẫu và cho người dùng sửa kết quả trước khi xuất JSON |
| MVP bắt buộc | OCR; schema extraction; confidence; review UI; validation; export; synthetic/sample data only |
| Công nghệ gợi ý | Python; OCR; vision-language model; React/Vue |
| GitHub evidence bắt buộc | Golden dataset; field-level metrics; error taxonomy; model/config versioning |

Không có rubric, số người/số ảnh tối thiểu, deadline, điểm số hay cam kết độ chính xác đã biết. Không giả định bắt buộc hỗ trợ đồng thời hóa đơn và đơn từ. VLM là gợi ý, chưa phải engine bắt buộc.

## FOUNDATION_REQUIRED

Nền phải chạy local được, có backend/frontend, contract nguồn chuẩn, normalization/validation có tests, interface OCR/extraction, fixture có provenance, evaluator kiểm tra được, CI/config collaboration, backlog/ADR và verification trung thực. Đánh giá AI dùng prediction trước review; fixture không là evidence chất lượng model. Không gọi AI trả phí/tải model lớn chỉ để dựng nền.

## PROVISIONAL và FUTURE_OPTION

Đơn đề nghị đánh máy, 7 trường, một trang, PNG/JPG; React + FastAPI, SQLite dự kiến cho MVP, uv/npm, không job queue: provisional, xem [decision log](../adr/README.md). OCR engine, lựa chọn hỗ trợ hóa đơn, quy mô dataset, ngưỡng chất lượng, tên/handle/deadline/budget: TBD, do vai trò điều phối phối hợp nhóm xác nhận qua BL-001/002/008/010. PDF, VLM, line items, chữ viết tay, đa trang: future option; cần ADR riêng. Không tự làm fine-tuning, thanh toán, đa tổ chức hoặc hạ tầng phân tán.

Foundation không triển khai upload, OCR/extraction thật, persistence, review sửa/lưu/xác nhận hoặc export từ revision lưu. [Backlog](../planning/backlog.md) mô tả các bước đó. Validation đạt không chứng minh khớp ảnh; OCR đúng chữ không chứng minh ánh xạ đúng; confidence chưa calibrated không phải xác suất đúng. Thiếu bằng chứng phải abstain/null.
