# ADR và decision log

ADR ghi context, options, decision, consequences, status và revisit conditions. Trạng thái các quyết định dưới đây: **đã áp dụng cho scaffold; PROVISIONAL cho sản phẩm cuối**, không tuyên bố nhóm đã duyệt. [Template](template.md).

| Quyết định | Hiện tại/loại | ADR hoặc công việc xác nhận |
| --- | --- | --- |
| Monorepo, backend modular | PROVISIONAL | [0001](0001-monorepo.md) |
| React/TS/Vite, FastAPI/Pydantic, uv/npm, SQLite dự kiến | PROVISIONAL | [0002](0002-stack.md) |
| Models sinh schema/OpenAPI/types | FOUNDATION_REQUIRED | [0003](0003-contract-source.md) |
| Fixture explicit, không fallback | FOUNDATION_REQUIRED | [0004](0004-fixture-mode.md) |
| OCR + rules baseline trước VLM | PROVISIONAL | [0005](0005-baseline.md), BL-002/004 |
| Đơn đề nghị, typed, PNG/JPG một trang, synthetic | PROVISIONAL / DATA-01 COURSE_REQUIRED | [0006](0006-data-scope.md), BL-001 |
| Bắt buộc cả hóa đơn và đơn từ? | Chưa giả định; TBD | Điều phối đối chiếu giảng viên/nhóm, BL-001 |
| OCR engine/model weights | TBD | Spike BL-002 rồi ADR; không lấy package version làm weights version |
| VLM/LLM, PDF, line items | FUTURE_OPTION | BL-011/ADR riêng nếu chọn; header/totals vs line items cần scope riêng |
| Quy mô data, SLA/độ chính xác, confidence threshold | TBD | BL-008/009/010 sau baseline; không đặt số giả |
| Thành viên/handles/deadline/budget/license/kênh bảo mật | TBD | Điều phối xác nhận; docs/team/roles và governance |

MVP requirements giữ loại COURSE_REQUIRED; scaffolding rules FOUNDATION_REQUIRED; lựa chọn thay đổi được PROVISIONAL; mở rộng chưa giao FUTURE_OPTION. Đổi ADR cập nhật traceability và config/evidence liên quan.
