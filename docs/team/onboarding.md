# Onboarding

1. Đọc [README](../../README.md), [scope](../requirements/scope.md), [traceability](../requirements/traceability.md), [ADR](../adr/README.md); hiểu foundation khác MVP và fixture khác engine.
2. Kiểm tra Python/uv/Node/npm theo runtime pins; `uv sync --project backend --locked`, `npm --prefix frontend ci`, copy `.env.example` vào `.env` để explicit fixture. Chạy hai terminal theo README, xem API capabilities và mẫu UI.
3. Chạy checks README; nếu lỗi đọc [troubleshooting](../operations/troubleshooting.md). Fixture evaluation chỉ kiểm tra công thức, không model quality.
4. Chọn [backlog](../planning/backlog.md) đã DoR, đọc contracts/guideline data/ADR liên quan, tạo issue/branch và cập nhật owner thật khi biết. Không sửa contract âm thầm.
5. PR mô tả behavior/tests/limitations và evidence, nhờ review chéo; remote owner cấp quyền/rulesets theo checklist. Không cần API key/GPU để bắt đầu foundation.

Trước lần xử lý tài liệu/model thật, chốt scope, data permission, provider/model config/budget, split/evaluation protocol. Giữ annotations ngoài inference và runtime artifacts ngoài Git.
