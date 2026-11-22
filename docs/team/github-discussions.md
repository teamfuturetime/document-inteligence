# Trao đổi trên GitHub Discussions — thành viên và agent

Vào [Discussions của dự án](https://github.com/teamfuturetime/document-inteligence/discussions).
Nhóm dùng nơi này để trao đổi phương án, đặt câu hỏi và chốt kế hoạch chung. Mỗi thành viên
dùng tài khoản của mình; agent hỗ trợ tìm hiểu, soạn và đăng trong phạm vi được người đó giao.
Không tạo cuộc hội thoại hoặc sự đồng ý thay cho thành viên khác.

Đọc cùng [quy trình nhận việc](github-collaboration.md), [AGENTS.md](../../AGENTS.md) và
[CONTRIBUTING](../../CONTRIBUTING.md). Hướng dẫn này không tự cấp quyền ghi GitHub cho agent;
thành viên có thể dùng prompt ở mục 8 để giao việc và cấp quyền đăng có giới hạn.

## 1. Bắt đầu cùng nhóm

1. Nhóm trưởng mở hoặc tái sử dụng một topic **General** cho đợt phối hợp, nêu mục tiêu,
   các quyết định còn mở và những người cần góp ý. Liên kết issue điều phối và Project.
2. Thành viên có công việc liên quan đọc topic và các replies trước khi trả lời. Đưa thông tin
   từ phần mình phụ trách: dependency, rủi ro, phương án hoặc điều cần người khác hỗ trợ.
3. Khi nhận phản hồi, trả lời đúng thread để người đọc theo được vấn đề; nêu rõ điểm đã thay
   đổi hoặc còn bất đồng. Không chỉ để kết quả trong cửa sổ chat với agent.
4. Người chủ trì ghi kết luận, phần còn chờ và các issue triển khai. Người nhận task xác nhận
   trên **issue** bằng tài khoản của mình; reviewer thực hiện review trên **PR**.
5. Khi có kết quả mới làm thay đổi kế hoạch, cập nhật thread bằng link issue/PR/CI cụ thể.
   Không chép toàn bộ log hoặc đăng lại nội dung không thay đổi.

Mọi thành viên đang tham gia đợt làm việc cần đóng góp góc nhìn của phần mình khi có câu hỏi
hoặc quyết định ảnh hưởng đến mình. Không đặt số comment/ngày, tạo topic cho từng commit,
hoặc bắt người không liên quan viết ý kiến cho đủ lượt. Nếu chưa có bằng chứng, ghi điều cần
kiểm tra thay vì bịa nhận xét hay kết quả chạy thử.

Để bắt đầu từ trạng thái hiện có, nhóm trưởng có thể dùng topic kế hoạch gắn với
[issue #40](https://github.com/teamfuturetime/document-inteligence/issues/40) và
[Project](https://github.com/orgs/teamfuturetime/projects/1). Đây là gợi ý mở topic, chưa phải
URL của một Discussion đã đăng. Giữ lịch sử #40; khi có Discussion thật thì liên kết hai chiều,
dùng Discussion cho trao đổi và giữ phân công/acceptance ở issues.

## 2. Chọn đúng nơi và category

| Nội dung | Nơi dùng | Đầu ra cần có |
|---|---|---|
| Kế hoạch đợt, thứ tự tích hợp, quyết định ảnh hưởng nhiều module | Discussion **General** | Phương án, dependency, người chốt, kết luận |
| Ý tưởng cần đánh giá trước khi giao triển khai | Discussion **Ideas** | Vấn đề, lợi ích, chi phí/giới hạn; chưa tự coi đã được duyệt |
| Câu hỏi setup, contract hoặc cách vận hành chưa rõ | Discussion **Q&A** | Điều đã đọc/thử, môi trường, câu hỏi và câu trả lời kiểm chứng được |
| Thông báo chính thức đã được người có trách nhiệm duyệt | Discussion **Announcements** | Nội dung và người chịu trách nhiệm; không tự đăng thông báo thay nhóm trưởng |
| Lấy ý kiến giữa các lựa chọn rõ ràng | Discussion **Polls** | Lựa chọn và tiêu chí; số phiếu không thay quyền quyết định hoặc review |
| Chia sẻ demo/kết quả thực có ích cho nhóm | Discussion **Show and tell** | Link PR/SHA, cách tái lập và giới hạn; chỉ dùng sample/synthetic hợp lệ |
| Bug đã xác định, đầu ra triển khai, nhận việc hoặc blocker của task | **Issue** | Tái hiện/acceptance, owner, dependency và kiểm tra |
| Nhận xét về file/dòng code, CI, approve/request changes | **PR review** | Review của đúng người trên bản mã được kiểm tra |

Các category trên đã có trong repo khi kiểm tra ngày 23/11/2026; dùng category hiện có phù hợp.
Không cần tạo category mới để bắt đầu. Khi có bug cụ thể trong một topic Q&A, tìm/tạo issue
theo quyền được giao rồi liên kết, không giấu bug chỉ trong thảo luận.

Discussion không thay issue nhận việc, PR approval, required checks hoặc quyền merge.
Một reaction, phiếu bầu, câu “OK”, comment của agent khác hay sự im lặng không phải bằng chứng
mọi người đã đồng ý hoặc reviewer đã approve.

## 3. Mở một topic có thể trả lời

Tìm trước theo từ khóa, issue/PR và category, đọc cả chủ đề cũ có liên quan. Dùng lại topic
cùng vấn đề; chỉ tách khi có câu hỏi/đầu ra thảo luận độc lập và liên kết topic nguồn.
Tiêu đề nên là câu hỏi hoặc quyết định cụ thể, ví dụ:

- `[Kế hoạch] Thứ tự tích hợp đợt OCR local tiếp theo`
- `[Hỏi đáp] Khi nào dùng doctor, khi nào đọc readiness?`
- `[Đề xuất] Cách người dùng đối chiếu vùng evidence PDF`

Đây là ví dụ tiêu đề, không phải task hay quyết định mới đã được nhóm duyệt.
Trên giao diện: **Discussions → New discussion → chọn category → nhập title/body →
Start discussion**. Agent có thể dùng công cụ GitHub/API đang có nếu đã được phép; không
bịa lệnh CLI, số topic hoặc URL khi thao tác chưa thành công.

Mẫu mở topic:

```markdown
## Cần trao đổi/chốt điều gì?
Một câu hỏi hoặc quyết định cụ thể; vì sao cần bàn lúc này.

## Bối cảnh và nguồn
Issue/PR/ADR liên quan, source SHA nếu nói về mã, điều đã kiểm tra và điều chưa biết.

## Phương án
A: hành vi, lợi ích, chi phí/rủi ro.
B: hành vi, lợi ích, chi phí/rủi ro.
Khuyến nghị ban đầu và lý do; nếu là Q&A thì nêu điều đã thử thay phần này.

## Cần ai góp ý?
Các vai trò/thành viên thực sự liên quan và câu hỏi dành cho từng phần.
Người chủ trì/người có quyền chốt; mốc cần phản hồi nếu nhóm đã thống nhất.

## Bước tiếp theo
Điều gì cần xác minh trước khi chốt; issue triển khai hiện có nếu có.
```

Không bắt buộc mọi Q&A có hai phương án hoặc mời cả nhóm. Chỉ mention người có thông tin
cần thiết; không tag hàng loạt hoặc đặt deadline thay người khác.

## 4. Phản hồi có ích bằng tài khoản của mình

Trả lời câu hỏi đang mở, chỉ ra điểm đồng ý/chưa đồng ý và lý do. Với nhận định kỹ thuật,
link file/commit/test/CI hoặc tài liệu nguồn; phân biệt quan sát, suy luận và đề xuất.
Khi chưa chạy, ghi rõ **chưa chạy**, không dùng kết quả người khác như kết quả của mình.

```markdown
Phần tôi phụ trách/liên quan: ...
Đã đọc/kiểm tra: link + SHA hoặc ca/lệnh thực chạy; phần chưa kiểm: ...
Ý kiến hoặc câu trả lời: ...
Ảnh hưởng/dependency và cách kiểm chứng: ...
Bước tôi đề xuất hoặc câu hỏi còn mở: ...
```

Ví dụ phản hồi về thứ tự tích hợp: nêu PR nền nào phải vào main trước, file nào dự kiến
conflict và cần giữ những tests/guards nào. Không chỉ nói “merge hết” vì CI của từng nhánh
xanh. Ví dụ Q&A vận hành: đọc runbook, nêu doctor là probe offline còn readiness là endpoint
của app đang chạy, kèm link nguồn; không tự migrate DB thật để tạo một câu trả lời.

Một người có thể sửa/bổ sung cùng phản hồi khi cần làm rõ. Khi có kết quả mới quan trọng,
trả lời tiếp thread với bằng chứng mới. Không tách từng câu thành comment, viết cùng một
ý dưới nhiều topic hoặc tạo nhiều tài khoản để tự phản biện/tự đồng ý.

## 5. Chốt quyết định và nối với công việc thật

Người chủ trì tổng hợp các phương án, bằng chứng và ý kiến còn khác nhau. Phân biệt:

- **Thông tin đã xác minh:** có nguồn/cách kiểm tra, chưa nhất thiết là quyết định triển khai.
- **Đề xuất/chờ phản hồi:** chưa được người có trách nhiệm chốt; không coi hết thời gian chờ
  hoặc thiếu phản đối là đồng ý.
- **Đã chốt:** ghi ai quyết định và link phản hồi/quyền được giao thực tế. Thay đổi phạm vi,
  ưu tiên hoặc quyết định ảnh hưởng nhiều module do nhóm trưởng điều phối với các owner.

Mẫu kết luận:

```markdown
Trạng thái: Đề xuất / Chờ xác minh / Đã chốt / Hoãn.
Quyết định và lý do: ...
Người chốt + căn cứ/link phản hồi thật: ...
Phương án chưa chọn hoặc giới hạn còn lại: ...
Issue triển khai/acceptance và dependency: ...
Owner/reviewer đề xuất; ai đã nhận, ai còn chờ xác nhận: ...
Khi nào cần xem lại quyết định: ...
```

Sau kết luận, tạo hoặc cập nhật issues độc lập khi được phép, gắn acceptance và link Discussion
thật. Người nhận xác nhận trên issue; PR link issue và Discussion khi quyết định đó ảnh hưởng
diff. Thay đổi kiến trúc/contract quan trọng cần ADR/tài liệu nguồn chuẩn theo quy trình repo.
Không tạo ADR cho mọi câu hỏi đơn giản.

Q&A: tác giả hoặc người có quyền chỉ **Mark as answer** khi câu trả lời thực sự giải quyết
câu hỏi. General/Ideas: ghi kết luận rõ trong topic; không dùng một dấu “answered” để giả
quyết định toàn nhóm. Discussion đã chốt không tự cấp phép merge, đổi quyền/settings,
deploy, dùng dịch vụ trả phí hoặc mở rộng phạm vi sản phẩm.

## 6. Quy tắc cho agent ở mỗi lượt làm việc

1. Đọc AGENTS, hướng dẫn này, issue được giao và Discussion liên quan. Xác minh tài khoản
   đang đăng nhập, ví dụ `gh api user --jq .login`; phải khớp tài khoản người điều khiển.
   Không tự chuyển tài khoản hoặc dùng token/người khác.
2. Đọc đủ body, comments, replies và kết luận hiện tại trước khi đăng. Nếu API có pagination,
   lấy các trang cần thiết; không phản hồi chỉ dựa vào title, preview hay summary thiếu thread.
3. Kiểm tra câu hỏi còn mở và ý kiến trùng. Khi có thông tin mới thuộc phần việc của mình,
   soạn phản hồi ngắn theo mục 4; dẫn nguồn/SHA thật và nói rõ kết quả nào do agent kiểm.
4. Nếu đã được cấp quyền đăng trong task, thực hiện trong phạm vi đó, không xin lại từng
   comment. Nếu chỉ được soạn tài liệu/dự thảo, lưu nội dung để người dùng duyệt; không tự
   đăng. Nếu thiếu quyền hoặc sai account, dừng bước ghi, tiếp tục phần đọc/soạn an toàn.
5. Không viết “cả nhóm thống nhất”, “X đã đồng ý/đã nhận việc”, “đã test/approve” nếu không có
   căn cứ. Không tự trả lời bằng danh tính thành viên khác hoặc biến ý kiến agent thành ý kiến
   được người điều khiển xác nhận khi họ chưa chốt; ghi **đề xuất/chờ xác nhận** khi phù hợp.
6. Khi phụ thuộc quyết định chưa chốt, báo blocker đúng thread/issue và tiếp tục phần độc lập
   đã được giao. Không tự thực hiện phần phụ thuộc bằng cách đoán ý người khác. Không tự đặt
   lịch đăng/poll liên tục hoặc tạo comment định kỳ chỉ để có hoạt động.
7. Sau thao tác ghi, đọc lại để kiểm nội dung/URL. Cuối lượt báo đã đọc gì, đã đăng ở đâu,
   điều đã chốt thực tế, phần chờ ai và bước tiếp theo. Không báo “đã đăng” khi chỉ có draft.

Không đưa secrets, token/cookie, dữ liệu người dùng, DB/uploads/model weights, raw OCR/native
stderr hoặc log chứa thông tin nhạy cảm vào topic. Chỉ dùng mẫu synthetic/sample được phép;
ảnh/demo đã kiểm nội dung và kết quả thật. Không lập bảng chấm điểm/đếm đóng góp cho giảng viên.

## 7. Đưa hướng dẫn tới các máy khác

Hướng dẫn cần vào main qua PR/checks/review trước khi được xem là quy ước đã tích hợp. Sau đó,
thành viên cập nhật main theo CONTRIBUTING; task branch cập nhật bằng quy trình merge main
đã thống nhất, không ghi đè thay đổi local hoặc tự rebase/force-push. Agent đọc lại AGENTS và
file này khi nhận task. Nếu đang xem bản PR chưa merge, ghi rõ đó là bản đề xuất.

Đọc hướng dẫn không tự tạo một Discussion, không tự gửi thông báo cho cả nhóm và không thay
bằng chứng tham gia của mỗi tài khoản. Nhóm trưởng mở topic thật khi đã muốn trao đổi chủ đề
cụ thể; từng thành viên dùng agent của mình để tham gia theo quyền được giao.

## 8. Prompt giao cho agent của mỗi thành viên

Thành viên điền tài khoản, task và topic của mình rồi gửi **nguyên khối** dưới đây cho agent.
Chỉ dùng khi muốn cấp quyền đăng trong phạm vi này; nếu chỉ muốn draft, thay dòng cấp quyền
bằng “Chỉ soạn nháp, chưa đăng GitHub”.

```text
Đọc AGENTS.md, docs/team/github-collaboration.md và docs/team/github-discussions.md
trong repo teamfuturetime/document-inteligence trước khi làm.

Tài khoản GitHub của tôi: <handle của chính tôi>.
Issue/phạm vi tôi được giao: <URL issue hoặc mô tả phạm vi đã được giao>.
Discussion cần tham gia hoặc câu hỏi muốn mở: <URL thật hoặc chủ đề cụ thể>.

Tôi cho phép agent dùng đúng tài khoản của tôi để tìm, mở hoặc trả lời Discussion
liên quan phạm vi trên và liên kết/cập nhật issue của tôi khi có thông tin mới.
Không cần hỏi lại từng phản hồi trong phạm vi đó. Quyền này không bao gồm nhận việc,
phát biểu/đồng ý thay người khác, approve/merge PR, đổi settings/quyền, xóa refs
hoặc triển khai ngoài phạm vi được giao.

Trước khi đăng, xác minh account khớp tôi; đọc đủ topic/replies, issues/PR và mã
liên quan, tìm trùng và kiểm nguồn/SHA. Nếu đã có topic cùng vấn đề thì tham gia
topic đó. Chỉ đăng khi có câu trả lời, bằng chứng, phương án hoặc blocker thực.
Phân biệt đã chạy, chưa chạy, suy luận và đề xuất; ghi rõ có agent hỗ trợ.
Không bịa kết quả, ý kiến/đồng thuận, người nhận việc hoặc URL.

Hãy thực hiện phần trao đổi thuộc công việc của tôi, ghi quyết định đúng người có
quyền chốt và link issue/PR khi có thật. Chưa có kết luận thì ghi chờ xác nhận,
không coi im lặng là đồng ý và tiếp tục các phần độc lập đã được giao.
Cuối lượt gửi URL đã đăng, tóm tắt nội dung mới, điều còn chờ ai và bước tiếp theo.
Nếu chưa đăng được, trả lại draft và lý do cụ thể, không báo đã hoàn tất trên GitHub.
```

Tham khảo thao tác giao diện, quyền tham gia và accepted answer tại
[GitHub Docs: Participating in a discussion](https://docs.github.com/en/discussions/collaborating-with-your-community-using-discussions/participating-in-a-discussion).
