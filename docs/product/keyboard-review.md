# Keyboard review — Refs #51

Phạm vi: hành trình review/autosave/recovery, không khẳng định WCAG conformance toàn app.
Nhánh từ main0064e90, không cherry-pick PR #63 chưa merge và không đổi error guidance/readiness #49/#50.

| Tình huống | Focus / thông báo |
| --- | --- |
| Mở tài liệu hoặc run | Tiêu đề review nhận focus, Tab đi tới các controls native |
| Autosave nền | Không chuyển focus editor; status polite/atomic chỉ đổi khi trạng thái đổi, không theo nội dung từng phím |
| Manual save lỗi / recovered draft | Alert có tên nhận focus, chỉnh sửa vẫn giữ |
| Lỗi nền khi đang nhập | Alert thông báo nhưng input vẫn giữ focus |
| Đối chiếu 409/recovery | Region có tên nhận focus; Tab tới hành động giữ/bỏ |
| Giữ/bỏ chỉnh sửa, retry save thành công | Trở về field đầu tiên có thể sửa |
| Confirm thành công | Đợi trạng thái confirmed render rồi focus export |
| Retry ảnh nguồn | Trở về region preview; mô tả vùng chữ theo field đang chọn |

Tab/Shift+Tab dùng thứ tự DOM, không positive tabindex hoặc key handler chặn phím.
Enter/Space giữ hành vi button native. Heading/alert/region chỉ có tabindex=-1 cho focus có chủ đích.
Preview có alt ảnh, tên field và mô tả số vùng/thiếu bằng chứng; không tự suy ảnh đã OCR đúng.

Giữ thuật toán debounce/ACK serialization, explicit reviewed_value=null, expected_run_id,
expected_revision/expected_status CAS, owner/session recovery và export từ revision persisted.
Không tự retry write khi recovery/lỗi. Giữ source key của editor khác theo implementation #23.

Component tests kiểm focus/role/name/description, null recovery, foreign key ownership,
background lỗi không giật focus và manual retry. Browser keyboard chạy ở 1280px và 390px:
mở bằng Tab/Enter → xóa null → autosave/validation → 409/compare/giữ → retry → reload/recovery/
discard → confirm/export; Tab rời nút export để kiểm không trap. HTTP/inference là doubles
synthetic có assertions revision/status/null/export, không là native OCR hoặc kiểm screen reader thật.
CI E2E hiện có tự tìm keyboard-review.spec.ts; chạy riêng không cần native backend:
`cd frontend` rồi `npx playwright test --config playwright.keyboard.config.ts`.
