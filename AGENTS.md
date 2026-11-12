# Hướng dẫn cho coding agents

- Đọc [scope](docs/requirements/scope.md), [contracts](contracts/README.md) và ADR liên quan trước khi sửa; giữ requirement IDs và ranh giới FOUNDATION/PRODUCT_MVP.
- Kế thừa mã và thay đổi của người khác; không reset, đổi remote, force-push hoặc bịa đóng góp.
- Backend domain models là nguồn chuẩn. Đổi schema/API phải cập nhật version, generated contracts, frontend types, examples và tests; không sửa bản sinh bằng tay.
- Giữ prediction máy riêng với review. `is_reviewed=true` và `reviewed_value=null` là người dùng xóa, không fallback bằng toán tử `or`.
- Inference không đọc gold. Fixture phải bật rõ, không fallback khi provider lỗi; fixture metrics không phải benchmark. Không tối ưu trên test rồi báo là phép đánh giá độc lập.
- Chỉ synthetic/sample hợp lệ; secrets, upload, DB/cache và model weights nằm ngoài Git. Không bịa confidence, metrics, model versions, test results, người tham gia hoặc tài khoản GitHub.
- Không sửa expected tests để che bug; chỉ đổi khi yêu cầu/contract đổi có lý do. Thay đổi data/model/config cập nhật versions, hashes và evidence.
- Kiểm tra backend/AI: `uv run --project backend --locked ruff check backend scripts pipeline`, `uv run --project backend --locked ruff format --check backend scripts pipeline`, `uv run --project backend --locked pytest backend/tests pipeline/tests -q`. Native workflow: `uv run --project backend --locked python scripts/verify_product.py`; cần Tesseract/models thật, không skip/fallback.
- Contracts/data: `uv run --project backend --locked python scripts/generate_contracts.py --check`, `uv run --project backend --locked python scripts/check_data.py`, `uv run --project backend --locked python scripts/evaluate_fixtures.py`, `uv run --project backend --locked python scripts/check_repository.py`.
- Frontend: `npm --prefix frontend run contracts:check`, `typecheck`, `lint`, `format:check`, `npm --prefix frontend test`, `npm --prefix frontend run build`; các tên ngắn trước đó là npm scripts.
- Báo rõ lệnh đã chạy, kết quả và pending checks. Không tự triển khai cloud, mua dịch vụ, gửi thông báo hoặc đổi quyền repository ngoài phạm vi được giao.

## Consolidation và Git

- README root/scripts/dev.py là nguồn lệnh chạy; ADR0008 là nền hiện hành. Một frontend/backend/pipeline, không tạo app cạnh tranh trong archive.
- GitHub Flow: main ổn định → feat/fix/docs/test/chore ngắn hạn → PR/checks/review. Nhánh cá nhân/bài tập là ref lịch sử; không xóa hoặc đổi link nộp.
- Commit phần nhỏ hoàn chỉnh theo Conventional Commits, review status/diff, stage paths cụ thể, kiểm staged diff/check. Không commit output cá nhân, runtime/models/DB/secrets.
- Không push, merge, force-push, rebase/amend/reset, đổi default branch/quyền hoặc xóa nhánh khi chưa có ủy quyền. Gói thao tác GitHub phải có nội dung cụ thể để người dùng duyệt trước.

## Công việc môn học phải có dấu vết trên GitHub

- Đọc [hướng dẫn làm việc nhóm](docs/team/github-collaboration.md) trước khi nhận task. GitHub Issues là nguồn phân công chính; PR là nơi review; Discussions là nơi lập kế hoạch/quyết định mở. Không chỉ chia việc hoặc báo hoàn tất trong chat ngoài GitHub.
- Mục tiêu là ghi nhận đầy đủ công việc thật: nhiều phần việc độc lập, commits hoàn chỉnh, PR có review, issues có acceptance và discussions có kết luận. Không tạo commit rỗng, chia theo từng dòng/file, duplicate issue/PR, comment vô nghĩa, reopen/close hoặc đóng/mở lại PR để tăng số đếm. Không đặt quota commit/comment/ngày.
- Yêu cầu chỉ viết tài liệu/khảo sát không tự cấp quyền đăng nội dung lên GitHub. Khi task đã ủy quyền quy trình GitHub, thực hiện issue/comment/push nhánh task/mở PR trong phạm vi đó, không xin lại từng bước đã được duyệt. Merge, đổi settings/quyền và xóa refs vẫn cần ủy quyền riêng. Nếu thiếu quyền, chuẩn bị nội dung cụ thể và tiếp tục phần local; không báo đã đăng khi chưa có URL thật.

### Trước khi code hoặc sửa tài liệu

1. Kiểm tra `git status`, nhánh/base, trạng thái PR nền, issue và PR đang có; tìm trùng trước khi tạo. Repo đích là `teamfuturetime/document-inteligence`. Không dùng main chưa có nền để phát triển; theo CONTRIBUTING trong giai đoạn chờ PR nền.
2. Mỗi kết quả có thể nghiệm thu độc lập cần một issue: vấn đề, phạm vi có/ngoài, acceptance, cách kiểm tra, dependencies, area/priority/milestone phù hợp. Việc lớn dùng issue cha và checklist/link issue con; chỉ tách khi có đầu ra riêng, không tách bắt buộc thành code/test/docs.
3. Mỗi issue có một người chịu trách nhiệm chính đã nhận việc và reviewer khác người đó. Chỉ dùng tài khoản đã xác minh, không suy GitHub handle từ tên thành viên. Đề xuất phân công trên issue và chờ người đó xác nhận; assignee không thay cho bằng chứng đã đồng ý. Agent không nhận việc hoặc approve thay thành viên khác.
4. Người nhận việc xác nhận bằng comment của chính tài khoản mình: hiểu đầu ra, kế hoạch, dependency, reviewer dự kiến. Agent hỗ trợ soạn nội dung cho người đang điều khiển, không giả danh người khác. Khi phân công đã rõ và được ủy quyền, cập nhật assignee thật và link issue cha/con.
5. Tạo nhánh ngắn dạng `feat/<issue>-<topic>`, `fix/…`, `test/…`, `docs/…` hoặc `chore/…`. Nếu đang làm mới phát hiện bug/việc ngoài acceptance, tạo/link issue tiếp theo trong phạm vi được phép, không mở rộng PR âm thầm.

### Trong khi thực hiện

- Commit ngay mỗi phần nhỏ đã hoàn chỉnh và kiểm tra phù hợp, dùng Conventional Commits và `Refs #<issue-thật>`. Không đợi gom cả đợt nhiều task thành một commit; không commit phần hỏng chỉ để có hoạt động. Với nhiều task độc lập, hoàn thành/commit từng task theo thứ tự dependency.
- Một PR giải quyết một kết quả độc lập; nhiều commits liên quan có thể cùng PR. Tách PR khi mỗi phần có acceptance và có thể review/tích hợp riêng. Với PR phụ thuộc, ghi base/dependency rõ; không đếm lại cùng diff qua nhiều PR.
- Mở Draft PR sớm khi có diff hữu ích và đã được phép push/PR. Cập nhật cùng PR khi sửa theo review; không mở PR mới cho từng comment. PR ghi issue, trước/sau, nguồn kế thừa, checks đã chạy/chưa chạy và rủi ro.
- Dùng `Refs #N` cho phần việc chưa hoàn thành hoặc PR phụ thuộc. Chỉ dùng `Closes #N` khi PR vào default branch thực sự hoàn thành acceptance; không đóng issue cha khi chỉ xong một phần. Trong giai đoạn PR vào consolidation, giữ issue mở đến khi tích hợp/kiểm chứng đúng đích.
- Cập nhật issue tại mốc có thông tin mới: kế hoạch đã chốt, dependency/blocker, thay đổi phạm vi, sẵn sàng review, kết quả nghiệm thu. Đưa log ngắn/SHA/run URL phù hợp; không đăng nhiều comment cùng nội dung hoặc toàn bộ log runtime.
- Quyết định ảnh hưởng nhiều module, lựa chọn engine/schema hoặc kế hoạch tuần: dùng Discussion nếu đã bật, liên kết issues/PR; ghi phương án, lý do và kết luận. Bug và acceptance cụ thể nằm ở issue. Nếu Discussions chưa bật, dùng issue điều phối có mục thảo luận và ghi nhu cầu bật; không tự sửa settings hoặc tuyên bố issue là Discussion.

### Review và bàn giao

- Yêu cầu reviewer là thành viên thật; cung cấp checklist theo rủi ro. Reviewer tự dùng tài khoản mình gửi review có file/dòng hoặc ca nghiệm thu cụ thể. Không tự approve, dùng nhiều tài khoản hay tạo nhận xét thay người chưa review. Có thể approve khi đã đọc và kiểm chứng; không bắt buộc tìm lỗi giả.
- Đọc CI đúng head/merge SHA mới nhất; `Product checks` phải completed/success trước khi đề xuất merge. Không lấy CI xanh của nhánh/commit khác, không giảm checks để tăng số PR merged. Chạy kiểm tra phù hợp phần thay đổi, không chạy lặp chỉ tạo hoạt động.
- Trước khi commit: xem status/diff, stage đúng paths, `git diff --cached --check` và đọc staged diff. Giữ tác giả gốc; `Co-authored-by` chỉ cho người thực sự đóng góp và identity đúng. Không đổi author/email, backdate hay chia lại lịch sử để điều chỉnh thống kê.
- Người có quyền merge chọn merge commit theo quy trình nhóm để giữ commits hữu ích và lịch sử gốc; không tự đổi repo settings. Không xóa nhánh cá nhân/bài tập. Dọn nhánh task sau merge chỉ khi được phép.
- Sau tích hợp, nghiệm thu theo acceptance và cập nhật issue bằng PR/commit/CI URL thật. Đóng issue theo đúng kết quả, giữ bug phát hiện mới ở issue riêng. Đừng tuyên bố Done chỉ vì local tests pass hoặc PR vừa mở.
- Cuối task báo: issue/PR/Discussion liên quan, commits thuộc task, kiểm tra, kết quả review và phần pending. Không yêu cầu thành viên lập bảng thống kê đóng góp hoặc báo cáo chấm điểm; giảng viên tự đánh giá hoạt động trên GitHub.
