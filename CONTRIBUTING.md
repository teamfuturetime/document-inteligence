# Đóng góp

Đọc [onboarding](docs/team/onboarding.md) và [quy trình](docs/team/workflow.md). Chọn hạng mục [backlog](docs/planning/backlog.md), tạo issue có vấn đề/phạm vi, requirement IDs, acceptance criteria, kiểm tra và dependencies. Mã BL là mã local, không phải số issue GitHub.

`main` giữ nền có thể chạy. Dùng nhánh ngắn `feat/...`, `fix/...`, `docs/...`, `test/...`, `chore/...`; coding agent mặc định `codex/...` theo công cụ. Không force-push nhánh chung. Commit nhỏ, mô tả hành vi thật; không dựng lịch sử đóng góp. Nhánh đang bàn giao là `nhatquang`, không tự đổi remote/nhánh của nhóm.

**Definition of Ready:** biết vấn đề, scope, input/output, tiêu chí chấp nhận, dependencies và nguồn requirement. **Definition of Done:** hành vi đúng, checks phù hợp đạt, docs/contracts/version/evidence cập nhật, không có secret/dữ liệu trái phép và đã review theo quy trình nhóm. Không đo hoàn thành bằng số file, dòng code hoặc coverage tùy ý.

PR dùng [template](.github/PULL_REQUEST_TEMPLATE.md); nêu thay đổi, lệnh và kết quả thật, contract/data/config ảnh hưởng, rủi ro và giới hạn evidence. Đề xuất ít nhất một thành viên khác review khi có reviewer; đây chưa phải setting GitHub đã bật. CI xanh không thay thế kiểm tra nghiệp vụ hay đánh giá chất lượng AI. Chạy checks trong README trước khi gửi PR.
