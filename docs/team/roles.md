# Vai trò

Lượt 24/10 người dùng yêu cầu triển khai cả sản phẩm trên nhatquang; xem [handoff](../product/integration-handoff.md). Đây là phạm vi nhánh cá nhân, không xác nhận nhóm đã thay phân công hoặc merge nền.

Nhóm đã được người dùng xác nhận ngày 20/10/2026 gồm năm người; Tùng là nhóm trưởng, Quang có sở trường AI, mỗi người dành khoảng 2-3 giờ/ngày. Bảng dưới là phân công đề xuất để nhận việc. Xem [kế hoạch chi tiết và 45 task](../planning/team-delivery-plan-2026-10-20.md), gồm branch, owner module, reviewer, lịch tuần và tiêu chí hoàn thành.

| Vai trò | Trách nhiệm | Owner đề xuất |
| --- | --- | --- |
| Nhóm trưởng/kiến trúc/tích hợp | Scope, contracts, app wiring, CI/Docker, tích hợp PR, release và hồ sơ chung | Tùng |
| AI/OCR/extraction | Tiền xử lý, engine thật, field mapping, evidence, confidence và model/config versions | Quang |
| Backend nghiệp vụ/lưu trữ | Upload, document/run storage, migrations, immutable predictions, revision, confirm/export | Trí |
| Frontend/review | UI đối chiếu/evidence/keyboard, sửa/xóa/lưu, save/conflict/confirm/export và responsive | Thao |
| Data/evaluation/QA | Generator/sources/labels/splits, evaluator/metrics/taxonomy, system/E2E và evidence | Tuấn |

Trí/Thao/Tuấn chưa cung cấp sở trường; phân vai cần chính chủ xác nhận tại buổi nhận việc, không phải đánh giá năng lực cá nhân. GitHub handles/quyền, branch Tuấn và deadline giảng viên còn cần xác nhận. Mỗi tác giả tự viết unit tests và docs module mình; Tuấn không test thay mọi người, Tùng không tự duyệt PR của mình. Reviewer/backup được chỉ rõ trong kế hoạch. Không coi ai là người duy nhất hiểu một module.
