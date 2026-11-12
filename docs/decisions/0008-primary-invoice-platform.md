# ADR-0008: Một nền OCR hóa đơn local

Status: chọn cho nhánh `chore/repository-consolidation` theo phạm vi chủ dự án xác nhận ngày 2026-11-12; chưa merge main hoặc giả danh nhóm review. Baseline nguyên trạng: nhatquang `a03ea309ada1480e537cb7de8936ad0d52d53698`.

## Context/options/evidence

Main chỉ README; các hướng nhatquang, canhtung-main/solo, minhthao, congtri, tuannguyen khác schema/storage/UI. [Audit](../repository-audit.md) và [inventory](../branch-inventory.md) đối chiếu mã/test/CI, không xếp hạng bằng commit count. Người dùng chọn OCR hóa đơn local một người dùng, auth/mở rộng để sau.

1. Core Tùng: PNG/JPEG/PDF, schema/evaluation/browser tests tốt; phải bổ sung persistence, revisions và authoritative server export.
2. Solo: có UI/adapters/đơn sinh viên nhưng giữ hai app; không DB/history persisted. Chọn sẽ tiếp tục vấn đề nhiều entry points.
3. Minhthao: auth/CSRF/ownership và formats rộng; cần PostgreSQL + AI service để chạy đúng kiến trúc; contract khác, storage path portability test đang fail local. Không cần complexity này cho scope đã chốt.
4. Congtri: modular monolith và PDF; pipeline đồng bộ, không persisted revisions/history tương đương.
5. Nhatquang: SQLite + persisted bounded worker, immutable prediction, transaction revisions, backend confirm/export, model/config/evaluation lineage. Baseline74 offline tests và exact-SHA CI xanh. Đây là nền phù hợp nhất cho phạm vi đã chốt, không khẳng định OCR accuracy tốt nhất trên ảnh thật.

## Decision

Giữ cấu trúc `frontend/`, `backend/src/docintel/`, `pipeline/`, `contracts/`, `data/`, `evaluation/`, `scripts/`. Không tạo apps/packages, database/framework/microservice mới. Backend domain models là contract nguồn chuẩn; generated JSON/OpenAPI/TS không sửa tay. README root là điểm chạy duy nhất. Một application production; fixture là mode explicit trong cùng app, không fallback.

Giữ hóa đơn là mặc định UI và luồng nghiệm thu. Đơn đề nghị hiện có trong nền này tiếp tục hoạt động/test. CCCD, đơn sinh viên, VLM/OCR.space ở nhánh khác giữ ref/commit lịch sử, có backlog chuyển có chọn lọc. Không xóa các kiểu tài liệu vì khác trọng tâm.

## Compatibility/migration cost

Các API/schema cũ của Tùng/Thao/Trí không tương thích trực tiếp: multipart vs raw bytes, validation route/stateless vs persisted revision, schema keys/date/amount/null và geometry khác. Không alias âm thầm hoặc chuyển DB tự động. Runtime SQLite giữ nguyên; không có migration SQL mới cho consolidation. Dữ liệu của implementation khác chỉ migrate sau mapping spec + backup + roundtrip/conflict/authorization tests.

Chi phí thấp: docs/CI/dev commands/guardrails, không đổi inference/domain hoặc di chuyển data. Chi phí vừa: port PDF single-page, autosave và notification qua adapter có tests. Chi phí cao/để sau: multi-user auth, PostgreSQL migration, multi-page/CCCD/VLM. Trình tự và AC trong consolidation-plan; không tự gán người/deadline.

## Consequences/revisit

Một native run/DB, loopback single-user; không dùng cho dữ liệu nhạy cảm/public multi-tenant. Chưa PDF/line-items/handwriting. Không suy confidence heuristic là xác suất. Nền được đưa main qua PR có review và checks, giữ original history; không squash lại để thay tên tác giả. Xem lại ADR nếu auth/multi-user hoặc PDF/multi-page thành bắt buộc. Quyền/cấu hình GitHub chỉ chuẩn bị, đợi duyệt một lần cuối.
