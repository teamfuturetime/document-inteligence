# Quy trình nhóm

Scope/requirement → issue → branch nhỏ → code/docs/contracts → checks → PR → review → merge. [CONTRIBUTING](../../CONTRIBUTING.md) là nguồn DoR/DoD/branch/commit; [templates](../../.github/PULL_REQUEST_TEMPLATE.md) yêu cầu tests/evidence/rủi ro. Đề xuất main runnable, một reviewer khác khi có người; chưa cấu hình GitHub protection.

Issue feature ghi problem/scope/IDs/acceptance/dependencies; bug ghi repro/expected/actual; lỗi data/model có sample/run/config/prediction trước review/taxonomy/nguồn được phép. BL local không số issue thật. Không assignee/handles/labels giả. Điều phối chuyển backlog lên GitHub khi được nhóm ủy quyền, không tự mở hàng loạt hay mời thành viên.

Review cả semantics ngày/mã/null/revision/provenance/metrics, không chỉ CI. Data/evaluation và frontend/backend kiểm tra chéo API/schema; reviewer tải sample hợp lệ đối chiếu evidence. Chủ nhiệm vai trò TBD, không ai được coi là người duy nhất hiểu một module. Mỗi thay đổi model/data cập nhật version/hashes/report; merge không tạo model quality claim từ fixture.
