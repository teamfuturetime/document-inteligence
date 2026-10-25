# Quy trình nhóm

Kế hoạch cụ thể cho năm người từ 20/10/2026 nằm tại [phân công và lịch 10 tuần](../planning/team-delivery-plan-2026-10-20.md). Theo yêu cầu mới, đề xuất giữ năm nhánh cá nhân liên tục, PR theo lát cắt nhỏ, merge commits và đồng bộ main hằng tuần sau khi gom nền. Quy ước đó thay đề xuất branch ngắn trước đây trong thời gian dự án này nếu nhóm duyệt; không đợi cuối kỳ mới merge. Cấu hình bảo vệ nhánh/required checks và các thao tác gom nền vẫn cần người có quyền thực hiện.

Scope/requirement → task/issue trên nhánh cá nhân → lát cắt code/docs/contracts nhỏ → checks → PR → review → merge. [CONTRIBUTING](../../CONTRIBUTING.md) là nguồn DoR/DoD/commit; quy ước nhánh áp dụng theo kế hoạch mới ở trên. [Templates](../../.github/PULL_REQUEST_TEMPLATE.md) yêu cầu tests/evidence/rủi ro. Đề xuất main runnable, một reviewer khác khi có người; chưa cấu hình GitHub protection.

Mỗi task ghi path được sửa; một file chỉ có một người đang sửa tại cùng thời điểm. File chung/contracts/locks do Tùng điều phối từng lượt. Bàn giao producer-consumer ghi contract version, PR/merge SHA, checks và người nhận; consumer dùng fixtures có nhãn để làm phần độc lập trong lúc chờ. Chi tiết ở mục 5.1-5.2 và 6.4 của bản phân công.

Tùng hoặc Trí được bàn giao xếp hàng đợi merge theo dependency, ưu tiên đầu vào đang chặn người khác. Kiểm trên main mới sau tích hợp; nếu main lỗi thì tạm dừng merge feature và ưu tiên fix/revert qua PR. Chỉ ghi task delivered khi đã merge và kiểm chung; nghiệm thu cuối theo mục 16.1-16.2 trên một candidate commit, không cộng các bản chạy riêng thành sản phẩm hoàn thành.

Issue feature ghi problem/scope/IDs/acceptance/dependencies; bug ghi repro/expected/actual; lỗi data/model có sample/run/config/prediction trước review/taxonomy/nguồn được phép. BL local không số issue thật. Không assignee/handles/labels giả. Điều phối chuyển backlog lên GitHub khi được nhóm ủy quyền, không tự mở hàng loạt hay mời thành viên.

Review cả semantics ngày/mã/null/revision/provenance/metrics, không chỉ CI. Data/evaluation và frontend/backend kiểm tra chéo API/schema; reviewer tải sample hợp lệ đối chiếu evidence. Owners và reviewers theo [roles](roles.md) và bản phân công; không ai được coi là người duy nhất hiểu một module. Mỗi thay đổi model/data cập nhật version/hashes/report; merge không tạo model quality claim từ fixture.
