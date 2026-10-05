# Use cases

## UC-01 — Chọn schema và tải tài liệu (planned; BL-001/005)

Actor: người dùng. Preconditions: schema được hỗ trợ, dữ liệu synthetic/sample phù hợp. Happy path: chọn schema → chọn PNG/JPG → backend kiểm tra bytes/pixel/page → lưu Document + checksum/provenance → trả ID. Lỗi: 413 quá giới hạn, 415 không hỗ trợ, 422 schema/ảnh sai; retry chỉ sau sửa đầu vào. Postcondition: tài liệu hợp lệ được lưu bằng tên hệ thống sinh. Acceptance: không traversal, không nhận file chỉ dựa extension, UI nói rõ giới hạn và lỗi. Foundation chỉ catalogue mẫu, chưa có upload.

## UC-02 — Xem xử lý hoặc lỗi (planned; BL-003/004/005)

Actor: người dùng. Preconditions: Document tồn tại và provider ready. Happy path: tạo run → xem status pending/running/succeeded → mở prediction. Lỗi: provider 503, timeout/failed ghi trạng thái thật; retry tạo run mới với idempotency policy, không ghi đè review cũ. Postcondition: run/version/lỗi truy vết được. Acceptance: health không thay thế readiness; UI không giả xử lý fixture là OCR thật.

## UC-03 — Đối chiếu trường/bằng chứng (fixture UI; BL-004/006)

Actor: người dùng. Preconditions: run hợp lệ. Happy path: xem ảnh cạnh fields → chọn field → highlight spans nếu có → đọc raw/normalized, confidence method/reasons và validation. Lỗi: không evidence thì ghi unavailable/unknown; không vẽ tọa độ bịa. Postcondition: hiểu điểm cần review; prediction bất biến. Acceptance: label/keyboard, unknown confidence bằng chữ; ảnh và trường tương ứng. Foundation dùng fixture chỉ xem, spans giả lập từ renderer.

## UC-04 — Sửa và lưu draft (planned; BL-006)

Actor: người dùng. Preconditions: revision đang xem và run tồn tại. Happy path: sửa/xóa field → validation → lưu với expected_revision → backend tạo revision mới, lưu event; null đã review được giữ. Lỗi: mất mạng báo chưa lưu/cho retry; 409 revision conflict yêu cầu tải bản mới và đối chiếu; không mất thay đổi âm thầm. Postcondition: bản nháp có thể thiếu/sai kèm issues; prediction không đổi. Acceptance: sửa confirmed làm revision mới thành draft; không dùng `reviewed_value or machine_value`.

## UC-05 — Xử lý cảnh báo và xác nhận (planned; BL-006/007)

Actor: người dùng. Preconditions: draft đã lưu và revision mới nhất. Happy path: sửa errors, đọc/ack warnings có version, xác nhận explicit → backend validate → confirmed. Lỗi: 422 validation, 409 stale; không cho bịa trường bắt buộc unreadable. Postcondition: xác nhận gắn revision cụ thể. Acceptance: không tin approved flag client, thông báo giải thích field lỗi, yêu cầu ảnh tốt hơn nếu không đọc được.

## UC-06 — Xuất JSON (contract ví dụ; workflow planned BL-007)

Actor: người dùng. Preconditions: revision persisted + latest + confirmed + valid. Happy path: yêu cầu export bằng revision ID → server đọc bản lưu → validate → tạo ExportArtifact có document/run/revision/schema/provenance. Lỗi: 409 chưa confirmed/stale, 422 invalid, 404 missing. Postcondition: artifact không chứa ảnh/path local/secret/log; đúng revision. Acceptance: client không thể tự gửi final JSON để bỏ qua gate; draft export nếu bổ sung phải tên/payload riêng. Foundation không có endpoint export, chỉ schema/examples/tests.

## UC-07 — Đánh giá batch (fixture implemented; benchmark planned BL-009)

Actor: data/evaluation/QA. Preconditions: gold đúng ảnh, manifest hợp lệ, predictions trước review cùng config chốt. Happy path: kiểm tra manifest/split → inference thật ghi predictions (MVP) → evaluator → report + run metadata → phân tích taxonomy. Lỗi: ID trùng/path/checksum/leakage/provenance sai thì fail; mẫu số 0 trả null + lý do; unreadable loại value matching và thống kê abstain. Postcondition: report có nguồn và hashes. Acceptance: fixture report luôn evaluator_contract_check; test không dùng để tune. Foundation chạy entry point fixture, chưa chạy model.
