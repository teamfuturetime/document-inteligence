# Đối chiếu từng yêu cầu VT-044 - 23001945

Tất cả đường dẫn bên dưới tính từ `individual/VT044/`. Đây là kiểm chứng
local trên executable harness được đề cho phép, không phải production release.

| Yêu cầu | Bài làm/evidence | Trạng thái |
|---|---|---|
| Đúng SV, team, AI-02, repository, VT-044 | Trang đầu báo cáo; baseline `66074f4ecc384b6006ac8b574001a0b4aced86ef` | Đã đối chiếu attachment mới |
| 1 problem statement, 3-5 AC, >=2 NFC | Báo cáo mục 1: 1 problem, 5 AC, 4 NFC | Có |
| Invariant/contract quan trọng | Owner isolation; chỉ đổi tombstone, bảo toàn dữ liệu/tệp | Có |
| Plan/prompt/assumptions trước code, file dự kiến | `PLAN.md` trong C_RED; `PLAN_COMPLETION.md` trước phần bổ sung | Có, giữ đúng thứ tự thực tế |
| Review/bác bỏ >=2 điểm bằng source thật | Thiếu owner/shared key; retention xóa tệp và cascade child | Có evidence source tại baseline |
| Chính SV bác bỏ >=1 assumption | `evidence/student-review.md`: “Bác bỏ: key chung không phân biệt chủ sở hữu tài liệu” | Có phản hồi thực tế trong cuộc hội thoại |
| Strategy unit/integration/API/E2E và phần không cần | Mục 3; unit storage/security và E2E backend có sẵn được chạy trong regression | Có; không gọi harness là browser E2E |
| >=10 case đủ 6 cột | 18 case logic T01-T18, 34 instances; mục 3 | Có |
| State transition, data rationale | A->D, D->A, self-loops, denied/rollback transitions; fixed clock/data owners | Có |
| >=2 negative, >=1 failure path gắn R1 | Foreign reads/writes, spoofing, missing identity, flush-then-commit failure | Có |
| Vertical slice chạy được hoặc harness | `harness.py`: real models/repository/storage + owner/tombstone sidecar | Có; giới hạn integration nêu rõ |
| Git branch/baseline riêng | Local `bt3/23001945-vt044`; baseline hash ở trang đầu | Có local |
| Test RED đúng lý do trước patch | C_RED `911698f5b0a8e9942fb33f1bee7d480dae96b0c9`, `red.log`: 21 failed/7 passed | Có; setup errors tách riêng |
| AI patch nhỏ, review diff | C_IMPL `72c9bcaf1713c230669c6d0aec7759ec90a48c55`; `evidence/review.md` | Agent review có; SV vẫn cần hiểu từng dòng |
| GREEN/commit/file/lệnh tái lập | `green-completion.log`: 34 passed; regression 133 passed; README | Có |
| Mutation đảo boolean, nhánh/commit tạm | `mutate.py`, `mutation-completion.log`; != -> == | Bị T01-T03 phát hiện; bản sạch không đổi |
| Line/branch + risk coverage | 93/93 lines, 18/18 branches; traceability AC1-AC5 | Có; không suy luận toàn hệ thống từ 100% |
| >=2 flaky risks | Fixed clock/boundaries; 3 shuffled orders x34; same-ID contention; network review | Có, giới hạn nêu rõ |
| 200 tasks, p95 <=5s và kết luận trung thực | 4 HTTP runs giữ cả lỗi; ASGI 200/200, 1,200 valid requests, p95 1.136s | Đã đo; chỉ ASGI đạt, chưa nghiệm thu HTTP/production |
| Traceability AC/Risk->case->file->commit->result | Báo cáo mục 7 | Có |
| AI Usage Log, >=2 điểm AI chưa đáng tin | Phụ lục A; shared key và response echo target | Có, gồm phản hồi người dùng thật |
| Reflection 250-350 từ | Mục 8, kiểm tra word count bằng script xuất/QA | Có; bản AI hỗ trợ để SV rà soát |
| PDF đúng tên, <=8 trang chính | `BT3_23001945_VT-044.pdf`, 8 trang chính + phụ lục | Xuất và kiểm tra visual khi hoàn thiện |
| Trang đầu đủ thông tin và cam kết | Báo cáo trang 1 | Có văn bản cam kết; SV tự xác nhận trước nộp |
| README chạy test | `README.md` | Có |
| Link GitHub branch/PR | Chưa push theo lựa chọn rõ ràng của người dùng | **Còn thiếu theo đề, không tự công bố** |
| Không merge trước nhóm review | Nhánh/worktree riêng; không merge | Đã giữ |
| Nộp Google Classroom, không email | Hướng dẫn bàn giao local | **Người dùng tự nộp; chưa khai nhận đã nộp** |

Nguồn đề: attachment `b86c0633-cbc5-4669-9112-24c0d2475e08/Pasted text.txt`.
Không có nội dung Lecture 06/07 gốc trong workspace; không bịa quote/số slide.
