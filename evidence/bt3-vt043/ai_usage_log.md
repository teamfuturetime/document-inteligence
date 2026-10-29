# AI usage log — VT-043

## Nhiệm vụ và prompt chính

Người dùng giao tiếp tục implementation và testing BT cá nhân 3, AI-02 Document Intelligence: autosave OCR debounce 800 ms, optimistic concurrency, bảo mật và nguyên bản OCR; FT-01–10, CT-01–03, HTTP performance 80 tác vụ/p95 ≤ 2,5 s, mutation bỏ validation, coverage, regression, evidence và commit riêng. Yêu cầu thực thi và ghi bằng chứng thật; không push/merge/PR và không thay lịch sử `minhthao`.

AI đọc mã nguồn và test hiện có trước khi sửa. Một agent xử lý frontend, một agent backend, một agent concurrency/performance; agent chính phụ trách mutation, tổng regression/coverage, evidence và review. Các agent review chéo sau khi test ban đầu PASS. Quy trình: SPEC → TEST → CHANGE → VERIFY → REVIEW, rồi quay lại TEST khi review tìm lỗi.

## Assumptions được kiểm tra

- HEAD ban đầu đúng baseline `997da9f`; tracked working tree sạch. Hai tệp untracked cũ được giữ nguyên.
- Nhánh BT3 chưa tồn tại; tạo `bt3-vt043-autosave` từ HEAD của `minhthao` trước khi sửa. Không merge/push/PR.
- `ocr-review.patch` là patch readability cũ, không chứa autosave. Không áp lại patch hoặc tạo implementation trùng lặp.
- Vitest/RTL/jsdom đã có; chưa có browser E2E. SQLite có sẵn; không giả định PostgreSQL được kiểm chứng.
- FastAPI endpoint OCR là hàm sync, có thể chạy song song qua thread pool; mỗi HTTP request phải có Session riêng.
- Môi trường Python 3.14/package có sẵn khác pin dự án; bằng chứng chỉ áp dụng môi trường ghi trong báo cáo.

## Hai phương án thiết kế

**Chọn:** atomic conditional update theo revision/owner/status/OCR, tăng revision trong cùng SQL statement; chụp response trước commit và chỉ trả sau commit. Frontend serialize autosave, debounce và lưu snapshot từng request; so sánh nội dung/revision acknowledgement, bỏ response của instance đã unmount. Bản nháp chưa xác nhận được giữ trong tab browser với revision gốc để khôi phục sau điều hướng; không tự rebase conflict.

**Bác bỏ:** chỉ debounce/AbortController hoặc lấy document rồi gán ORM không có CAS. Hủy request ở client không bảo đảm server chưa ghi; hai tab vẫn có thể ghi đè nhau. Cho nhiều autosave cùng chạy với revision đọc từ render cũng tạo conflict không cần thiết và làm việc xác nhận draft phức tạp hơn. Không thêm hệ thống merge văn bản hoặc tự retry conflict vì có thể làm mất thay đổi của client khác.

## Lỗi/phát hiện và cách xử lý

| Phát hiện | Thay đổi/kiểm chứng | Evidence |
|---|---|---|
| Bản cũ nhận thiếu/sai/stale revision | Regression mới FAIL trước khi thêm CAS/schema; PASS sau sửa | `backend_implementation_before.log`, `backend_implementation_after.log` |
| Revision quá lớn gây lỗi driver hoặc nhận sai contract | Test trước FAIL, thêm giới hạn strict integer tương thích Integer | `backend_revision_bound_before.log`, `backend_revision_bound_after.log` |
| Refresh sau commit có thể lấy nội dung writer kế tiếp | Chụp snapshot trước commit; test giả lập writer tiếp theo trước serialization | `backend_response_snapshot.log` |
| Frontend chưa debounce/giữ đúng acknowledgement | FT fake timers/deferred promises FAIL trước patch, PASS sau patch | `frontend_fail_before_patch.log`, `frontend_test.log` |
| Response OCR cùng revision đến muộn làm UI confirmed trở về reviewed | Review chéo, test tái hiện FAIL, merge chỉ revision lớn hơn và khóa OCR khi action đang chạy | `frontend_equal_revision_fail_before_patch.log`, `frontend_test.log` |
| SPA menu/back có thể bỏ mất timer/draft khi unmount | Khôi phục draft theo document trong tab, giữ expected revision ban đầu; test điều hướng trước debounce | `frontend_test.log` |
| HTTP 200 hỏng JSON/ack khiến harness mất report hoặc đếm sai success | Bốn corruption tests FAIL trước fix, ghi `unexpected_error` và không công nhận winner sai | `performance_harness_fail_before.log`, `performance_harness_pass_after.log` |
| Một lần đo TCP có ReadError | Giữ toàn bộ run thất bại, điều tra và kiểm soát chính sách connection; xem báo cáo performance | `performance_transport_failure_*`, `performance_summary.md` |
| Hai schema fixtures cũ không truyền revision sau đổi contract | Bổ sung revision=0 và assert response; giữ required revision trong schema | `backend_coverage_initial.log`, `backend_schema_fixtures.log` |
| AI gọi coverage sai `--source` | Lần đầu dùng filename nên không thu data; lần sau dotted modules gây import sớm/lặp ORM. Sửa dùng thư mục rồi lọc lúc report | `backend_coverage_initial.log`, `backend_coverage_collection_failure.log`, `backend_regression.log` |
| Một frontend fixture của AI trả filename sai trong save response | Sửa fixture nhất quán với document; không nới assertion hoặc contract | Ghi nhận của agent; không có log FAIL riêng cho lỗi fixture này |
| Traceback fixture trong log đầu có token phiên test | Redact giá trị credential trong evidence trước commit, giữ kết quả test và traceback; không đưa cookie/password thật vào commit | Ghi chú chuẩn hóa/redaction trong `review_diff.md` |

Không dùng kết luận của AI làm bằng chứng đúng/sai. Các kết luận dựa trên test output, persisted-state assertions, mutation và mẫu đo được.

## Phạm vi tệp và human review

Danh sách tệp implementation/tests/harness và liên kết commit được ghi trong [review_diff.md](review_diff.md). Không sửa API auth, CSRF middleware, OCR engine, extraction/classification rules hoặc database thật. Dependencies bổ sung phục vụ ESLint/V8 coverage và công cụ test cục bộ; không thêm dependency ứng dụng runtime.

Human review cần tập trung: tương thích required `expected_revision` với client cũ; migration trên database triển khai; hành vi khi conflict (copy/đối chiếu, không tự ghi đè); vòng đời bản nháp tab browser; và giới hạn số liệu SQLite/TCP loopback. Browser E2E/manual journey, PostgreSQL và tải kéo dài chưa được thực hiện; không ghi chúng là PASS.

Traceability AC/risk → case → test file → code → evidence → commit nằm trong `review_diff.md`. Hash commit có thể tra bằng `git log --oneline bt3-vt043-autosave` và đường dẫn file tương ứng.
