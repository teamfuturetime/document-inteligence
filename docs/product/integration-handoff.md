> LỊCH SỬ bàn giao24/10: nền hiện hành đã chọn ở [ADR0008](../decisions/0008-primary-invoice-platform.md); xem [consolidation plan](../consolidation-plan.md) cho port và quy trình GitHub mới. Các đề xuất chọn nền Tùng dưới đây giữ làm tham chiếu, không là quyết định hiện tại.

# Bàn giao thay đổi trên nhatquang

Ngày 24/10 người dùng yêu cầu triển khai **cả sản phẩm trên nhatquang**. Yêu cầu này mở rộng khỏi phạm vi AI riêng trong bản phân công 20/10; không tuyên bố Tùng/Trí/Thao/Tuấn đã nhận lại vai trò hoặc main đã có nền chung.

Các thay đổi local cần nhóm review trước tích hợp: backend product workflow và contracts; pipeline AI; frontend workspace; synthetic dataset/evaluator; CI/Compose/runbook. Không merge toàn bộ nhánh khác để tạo nhiều app song song. Không tự commit/push/merge trong lượt triển khai.

## Thứ tự review đề xuất

1. Contracts/domain và ADR 0007; thống nhất schema keys/date/money/null/revision/error semantics.
2. Pipeline, model lock, source lineage, thực thi native và tests ở ranh giới adapter.
3. SQLite/storage/worker, review transactions và server export; Trí/Tùng review kỹ persistence/restart/conflicts.
4. Frontend workspace, source overlay, dirty-state và 409; Thao review kết nối actual API.
5. Data/evaluator/report/versioning; Tuấn đối chiếu nhãn và xem support/exclusions/unknown confidence.
6. Run checks, native E2E và clean environment trên đúng commit của PR; sau đó người có quyền mới quyết định merge.

## Điểm nối nếu nhóm chọn nền Tùng

| Trách nhiệm ở đây | Nơi nối ở nền Tùng | Điều kiện |
| --- | --- | --- |
| pipeline.service.DocumentPipeline.run(bytes, document_type) | pipeline entry point dùng chung API/evaluation | Chọn một runner, thêm adapter DTO; không giữ hai công thức extraction production |
| docintel.domain.documents | schemas/src/document_contracts | Port models như một nguồn chuẩn, regenerate schema/types và tăng version nếu semantics đổi |
| docintel.adapters.pipeline | Chỗ chuyển output OCR/extraction sang domain | page 0-based và frame preview phải được kiểm bằng geometry tests |
| DocumentService/repository/storage/worker | backend services và migrations | Giữ transaction stale-check+write, persisted jobs và explicit reviewed-null |
| features/documents | React UI chung | Dùng generated API client/types của nền được chọn, không JSON.stringify form để export cuối |
| evaluation.product | evaluation/src/document_evaluation | Giữ present/readable accuracy và TP/FP/FN, không đổi thành null-inclusive accuracy cùng tên |

Khi review góp phần cũ, giữ commit/SHA nguồn và người thực sự viết; không bịa account, reviewer approval hoặc đóng góp. File model `.traineddata`, `.env`, uploads/DB/cache và runtime reports không được stage. File `'` chưa theo dõi đã có trước lượt này, giữ nguyên và không thêm vào commit sản phẩm.
