# Live readiness — Refs #50

Consumer của [readiness #48](../operations/readiness.md), từ main `a9692a8` (PR #58 đã merge).
Không đổi backend API/schema/generated artifacts, OCR hoặc inference provider.

| Trạng thái | UI và hành động |
| --- | --- |
| ready | Backend trả Readiness200, session đã xác minh và capabilities đã tải; upload còn cần `ocr_ready`, file và xác nhận nguồn |
| not_ready | Readiness503 hợp lệ, không parse ErrorEnvelope; upload/reprocess/save/confirm/export tạm khóa |
| reconnecting | Network/timeout/body sai hoặc chưa xác minh lại session; giữ editor/draft và file upload đang chọn |

Status có tên `Trạng thái backend`, role status, live polite/atomic; không thay focus.
Readiness là startup snapshot của provider, không chứng minh model/tool vẫn không đổi
hoặc OCR chính xác. Không chuyển fixture khi mất kết nối.

## Polling và recovery

Chỉ một readiness cycle đang chạy; toàn cycle timeout8s. Healthy poll15s; 503/lỗi
backoff1/2/4/8/16/30s, cap30s. Nút Thử lại tối đa một lần bắt đầu/giây, không tạo
nhiều request song song. Hidden/unmount hủy timer/request; visible/online không
reset backoff hoặc tạo burst. Resume cần tối thiểu1s và giữ delay trước đó.

Sau khởi tạo/reconnect/visible hoặc chuyển not_ready→ready: xác minh `/auth/session`
rồi lấy capabilities bằng sessionFetch, kiểm revision cả sau đọc body. Healthy
poll không lặp capabilities/provider probe. Reconnect refresh schemas/list/insights
và tiếp tục GET trạng thái run cần thiết; không thay document editor đang mở.
AbortSignal, generation và keyed session boundary bỏ response cũ/cross-account.

Không tự replay upload/write. Upload lỗi mơ hồ giữ file và idempotency key cho
retry chủ động. Draft giữ nguyên khi offline; queued autosave bị gián đoạn cần
bấm Lưu nháp sau recovery, vẫn gửi run/revision/status CAS và explicit null.
Recovery sau reload vẫn đối chiếu server theo cơ chế cũ. Không tự confirm/export.

Session lookup lỗi mạng khi đã có identity giữ nguyên editor/owner key, đánh dấu
uncertain và chặn protected requests đến khi xác minh lại. Offline không là logout.
Verified401 hoặc identity đổi vẫn cleanup owner cũ và gỡ workspace. Khi chưa biết
identity, workspace vẫn bị khóa; readiness loop có thể khôi phục session lookup.

## Kiểm chứng

`npm --prefix frontend test`: fake clocks kiểm 200/503/model, backoff/counts,
single flight/timeout, manual retry storm, visibility/unmount, stale capabilities,
session uncertainty/401, null/CAS và không replay autosave.

Browser riêng không cần backend native:

```sh
cd frontend
npx playwright test --config playwright.readiness.config.ts
```

Ba ca Chromium: 1280px/390px, HTTP503→ready→disconnect→503→ready,
context offline + route abort, request counts, failed upload giữ key/file,
null draft/no write replay và explicit retry; response list alpha muộn sau đổi
beta, verified401 cleanup. Đây là synthetic HTTP/session/inference doubles,
không phải native OCR, screen reader audit hoặc WCAG conformance toàn app.
Spec cũng được CI browser hiện có tự tìm, không thêm job/hạ required checks.

Autosave HTTP harness có worker disabled/inference double từ trước; readiness
được double tường minh trong context thường và persistent restart. Native readiness
và owner checks tiếp tục ở suites backend/native/auth CI, không giả ready ở server.

## Đồng bộ PR chưa merge

Tại lúc triển khai: PR #63 (Draft, #49) và #64 (Ready, #51) đều chưa merge.
Không cherry-pick hoặc nhập diff của chúng. Dependency bắt buộc #48 đã có trên main;
hai PR trên chỉ là điểm cần kiểm tương thích sau tích hợp.

Sau khi từng PR merge, fetch và merge main vào branch task theo GitHub Flow;
giữ error guidance/retry guards của #63 trong Workspace, ghép guard backendReady;
giữ focus lifecycle/status semantics của #64 trong ReviewPanel, ghép manual-save
và resumeRequired của #50. Không ghi đè toàn file hoặc thay acceptance #49/#51.
Browser doubles của #63/#64 phải thêm Readiness body và session response hợp lệ.
Chạy lại fake-clock/component, readiness/keyboard/error-guidance/autosave/auth/native
browser suites và Product checks đúng head/merge mới trước review tích hợp.
