# Làm việc và nhận việc qua GitHub

Áp dụng cho nhóm tại [document-inteligence](https://github.com/teamfuturetime/document-inteligence). Mục tiêu: mỗi công việc thật có người nhận, đầu ra, review và lịch sử phối hợp rõ ràng trên GitHub. Đọc [README](../../README.md) để cài/chạy, [CONTRIBUTING](../../CONTRIBUTING.md) để kiểm tra và tích hợp. Agent đọc thêm [AGENTS.md](../../AGENTS.md).

## 1. Bắt đầu trong 10 phút

1. Dùng GitHub cá nhân, cung cấp handle cho nhóm trưởng; kiểm tra quyền truy cập repository. Không dùng chung tài khoản để commit/review cho nhiều người.
2. Kiểm tra `git config user.name` và `git config user.email`. Email commit cần gắn với GitHub của bạn (có thể dùng noreply chính xác từ Settings → Emails). Chỉ sửa cấu hình cho repo khi cần; không đổi author của commits cũ.
3. Đọc Issues và PR đang mở, đặc biệt PR nền. Khi main chưa chứa nền docintel, làm theo base tạm trong CONTRIBUTING; không tiếp tục nhánh cá nhân cũ theo thói quen.
4. Tìm việc chưa có người nhận, comment nhận việc theo mẫu bên dưới. Chờ xác nhận phân công trước khi làm việc có nguy cơ trùng với người khác.
5. Tạo nhánh theo issue, làm phần nhỏ, commit có nghĩa, mở Draft PR khi đã có diff hữu ích. Mời một thành viên khác review khi sẵn sàng.

## 2. Nội dung nào đặt ở đâu?

| Nội dung | Nơi ghi nhận | Kết quả cần có |
|---|---|---|
| Tính năng, bug, tests, docs, review dataset | Issue | Một đầu ra, acceptance, owner, dependencies |
| Giao/nhận việc và tình trạng blocked | Assignee + comment trên issue | Người nhận xác nhận, bước tiếp theo rõ |
| Đề xuất kỹ thuật nhiều phương án, kế hoạch/retrospective tuần | Discussion | Phương án, trao đổi có lý do, kết luận/link task |
| Mã và tài liệu cần tích hợp | Pull request | Diff có phạm vi, liên kết issue, checks/review |
| Phản hồi chi tiết vào thay đổi | PR review / review thread | Vị trí hoặc ca kiểm tra, yêu cầu cụ thể |
| Mốc bàn giao của nhóm | Milestone | Tập issues có điều kiện hoàn thành |

Chat riêng/họp có thể dùng để trao đổi nhanh; kết luận, phân công và thay đổi phạm vi phải được ghi lại trên GitHub. Không chép từng câu chat thành comment.

**Trạng thái lúc soạn ngày 12/11/2026:** Discussions của repo đang tắt. Người quản trị có thể bật ở Settings → General → Features → Discussions khi nhóm duyệt; xem [hướng dẫn GitHub](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/enabling-or-disabling-github-discussions-for-a-repository). Tài liệu này không tự bật tính năng. Trong lúc chờ, thảo luận ở issue điều phối; nếu sau này có Discussion, liên kết hai nơi và tóm tắt quyết định một lần.

## 3. Nhóm trưởng chia việc hoàn toàn trên GitHub

1. Mở/cập nhật một Discussion kế hoạch tuần; nếu chưa bật thì dùng một issue điều phối. Ghi mục tiêu, năng lực thực tế, dependencies và kết quả mong đợi. Dùng milestone sẵn có phù hợp; không tạo milestone trùng chỉ để có thêm số lượng.
2. Với mỗi tính năng lớn, tạo hoặc tái sử dụng issue cha. Chia thành issue con khi từng phần có đầu ra có thể nghiệm thu riêng; ghi checklist và link hai chiều, hoặc dùng sub-issues nếu giao diện/quyền hỗ trợ.
3. Mỗi issue con ghi phạm vi, acceptance, kiểm tra, nguồn code nếu port, dependency và người được đề xuất. Thống nhất owner chính và reviewer; không gán tất cả thành viên vào một issue để coi là đã đóng góp.
4. Thành viên comment xác nhận; sau đó cập nhật Assignees và milestone/labels. Nếu không đủ quyền assign, người có quyền thực hiện sau xác nhận. Không suy ra việc đã nhận chỉ từ tên trong tài liệu phân vai cũ.
5. Duy trì trạng thái bằng Projects nếu nhóm đã có board/quyền; nếu chưa có, ghi một dòng `Trạng thái: Ready / In progress / Blocked / In review / Done` trong issue. Không bắt buộc tạo board hay status labels mới để bắt đầu.
6. Kiểm tra blocked/review trước khi giao thêm việc. Quy ước khởi đầu: mỗi người một task chính đang làm, có thể song song review cho người khác; thay đổi theo năng lực và thỏa thuận trên issue điều phối.

Labels hiện có để dùng lại: `area:repo`, `area:ocr`, `area:review`, `area:data`; `priority:P0`, `priority:P1`, `priority:P2`; `migration`. Kiểm tra trên GitHub trước khi chọn, không giả định labels/assignee mới đã tồn tại.

### Ví dụ tách một việc OCR lớn

| Issue con đề xuất | Đầu ra có thể nghiệm thu | Phụ thuộc |
|---|---|---|
| Đặc tả PDF một trang và lỗi trả về | Quyết định limits, error cases, frame evidence được review | Issue PDF cha |
| Pipeline đọc PDF theo đặc tả | Code + tests decode/page/encryption/timeout | Đặc tả đã chốt |
| API/UI nhận và preview PDF | Upload, capabilities, preview và tests đồng bộ | Pipeline/contract sẵn sàng |
| Nghiệm thu PDF trên trình duyệt | Native E2E và runbook, kết quả thật | Luồng API/UI đã tích hợp |

Đây là ví dụ lập kế hoạch, chưa phải issues đã tạo hoặc phân công thật. Một bug nhỏ sửa bằng vài dòng kèm test có thể chỉ cần một issue/PR; không ép thành bốn phần.

## 4. Mẫu issue và nhận việc

Trước khi tạo issue, tìm theo từ khóa và xem backlog để tránh trùng. Dùng template Issues của repo; bổ sung các mục dưới khi thiếu:

```markdown
## Vấn đề và đầu ra
Người dùng gặp gì? Sau task hành vi/tài liệu nào thay đổi?

## Phạm vi
- Làm:
- Chưa làm:

## Nghiệm thu
- [ ] Hành vi/đầu ra kiểm chứng được
- [ ] Test/check hoặc review cần thiết
- [ ] Tài liệu/contract/evidence liên quan được cập nhật

## Phối hợp
Owner đề xuất: (handle đã xác minh, chờ xác nhận)
Reviewer đề xuất: (người khác, chờ xác nhận)
Dependency / issue cha: (link thật hoặc Không có)
Nguồn port: (branch/commit nếu có)
Trạng thái: Ready
```

Thành viên tự đăng comment nhận việc:

```markdown
Tôi nhận phần việc này sau khi nhóm xác nhận phân công.
Đầu ra tôi hiểu: ...
Kế hoạch và cách kiểm tra: ...
Dependency/cần hỗ trợ: ...
Reviewer đề xuất: ...
```

Nhóm trưởng xác nhận trên cùng issue; Assignees thể hiện người chịu trách nhiệm chính. Việc QA/review có đầu ra độc lập có thể có issue riêng; việc đọc một PR thông thường ghi bằng review, không cần tạo issue phụ cho mỗi comment.

Nếu bị chặn, cập nhật issue: đang thiếu gì, đã thử gì, link dependency, ai cần quyết định và bước còn có thể làm. Chỉ thêm thời hạn khi đã thống nhất; không tự tạo cam kết thay người khác.

## 5. Nhánh và commits

Sau khi main đã nhận nền chung, chạy từng lệnh:

```sh
git switch main
git pull --ff-only origin main
git switch -c feat/ISSUE_NUMBER-pdf-single-page
```

Thay `ISSUE_NUMBER` bằng số issue thật. Nếu main chưa có nền, theo CONTRIBUTING để branch từ consolidation; ghi base và dependency trong PR, không merge thẳng vào main khi thiếu nền. Không áp dụng chuỗi lệnh bằng cách ghi đè một working tree đang có thay đổi.

- Commit mỗi phần nhỏ hoàn chỉnh: một lỗi + regression test, một adapter chạy được, một cập nhật contract đồng bộ, hoặc một hướng dẫn nghiệm thu riêng.
- Dùng Conventional Commits, ví dụ `fix(api): reject encrypted PDFs` với body `Refs #<số issue thật>`; placeholder phải được thay trước khi commit.
- Code và tests cần nhau để thay đổi đúng thì đi cùng commit. Không chia theo từng file/dòng, không cố có số commits bằng nhau giữa thành viên.
- Trước commit xem status/diff, stage paths cụ thể, xem staged diff và chạy `git diff --cached --check`. Chạy checks phù hợp trước commit; không báo pass khi chưa chạy.
- Dùng danh tính của chính người thực hiện; ghi nguồn port và co-author thật. Không giả đóng góp, sửa ngày hoặc đổi author lịch sử. Khai báo AI hỗ trợ theo yêu cầu của môn học; người nộp chịu trách nhiệm hiểu và giải thích thay đổi.

## 6. Mở PR và review chéo

Push/mở PR khi đã được ủy quyền; mỗi thành viên nên tự tạo PR từ tài khoản mình cho phần mình phụ trách. Agent chỉ hỗ trợ trong tài khoản/phạm vi được giao. Không tạo PR dưới tên nhóm trưởng cho tất cả mọi người rồi coi là bằng chứng cá nhân tương đương.

1. Mở Draft PR khi có diff hữu ích; một kết quả độc lập tương ứng một PR. Có thể nhiều commits trong PR; đừng chờ gom mọi việc của tuần.
2. Dùng template PR: vấn đề, trước/sau, issue, test thực sự chạy/chưa chạy, nguồn kế thừa và giới hạn.
3. `Refs #N` liên kết phần việc đang làm. Dùng `Closes #N` trong body khi PR vào default branch hoàn thành issue; chỉ xong một phần thì không đóng issue cha. PR vào consolidation dùng `Refs` và kiểm tra issue sau khi thay đổi vào main. Xem [quy tắc liên kết GitHub](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue).
4. Khi sẵn sàng, chuyển Ready for review, request reviewer thật và cập nhật issue thành In review. Nếu dependency chưa xong hoặc CI fail thì ghi rõ.
5. Reviewer dùng Files changed → Review changes. Kiểm acceptance, diff, test phù hợp, null/revision/export semantics, dữ liệu và secret. Ghi đã kiểm tra gì, kết quả và điểm cần sửa; không chỉ comment “OK” để tăng lượt.
6. Tác giả trả lời từng điểm, thêm commit sửa vào cùng PR, ghi kết quả kiểm tra lại và nhờ re-review. Người thực sự kiểm tra xác nhận; không tự tạo review thay bạn cùng nhóm.
7. Người được phép merge kiểm `Product checks` completed/success trên SHA mới nhất, đủ review và hội thoại đã giải quyết. Đề xuất merge commit để giữ commits hữu ích; không tự thay settings hoặc bỏ protection. Chưa có quyền merge thì bàn giao, không tự merge.
8. Sau merge, đối chiếu acceptance và link PR/CI trên issue. Đóng nếu hoàn thành, hoặc giữ mở phần còn lại rõ ràng. Nhánh bài tập/cá nhân giữ nguyên; xóa nhánh task chỉ khi nhóm cho phép.

Mẫu review thực chất:

```markdown
Đã đọc: (file/luồng cụ thể)
Đã kiểm tra: (lệnh/ca thử, commit SHA)
Kết quả: ...
Cần sửa hoặc giới hạn còn lại: ...
```

Không cần tìm lỗi giả để có review. Nếu không có lỗi, nêu ngắn gọn phạm vi đã kiểm chứng rồi approve bằng tài khoản reviewer.

## 7. Discussions và nhịp phối hợp

- Mỗi tuần dùng một chủ đề kế hoạch/tiến độ chung khi có nội dung mới; thành viên báo phần mình bằng link issue/PR, blocker và bước tiếp theo. Không tạo một Discussion cho từng commit hoặc bắt mỗi người đủ số comment.
- Dùng chủ đề kỹ thuật riêng khi cần lựa chọn có tác động: engine OCR, schema, PDF geometry, cách đánh giá. Người đề xuất đưa phương án và bằng chứng; người khác phản biện có lý do. Kết luận liên kết task/ADR để triển khai.
- Q&A ghi câu hỏi tái hiện được và câu trả lời có cách kiểm tra; chọn câu trả lời khi thực sự giải quyết. Không tự dựng hội thoại nhiều tài khoản.
- Có thể dùng category sẵn có phù hợp. Tạo categories, bật Discussions hoặc Projects là thay đổi cấu hình cần người có quyền và sự đồng ý của nhóm; tài liệu không tự cấp quyền đó.

## 8. Checklist một task hoàn chỉnh

- [ ] Issue không trùng, có acceptance, owner đã nhận và dependencies rõ.
- [ ] Nhánh đúng nền; commits nhỏ hoàn chỉnh, tác giả/nguồn chính xác.
- [ ] PR liên kết issue, không gộp việc ngoài phạm vi.
- [ ] Checks phù hợp và CI đúng SHA có kết quả thật.
- [ ] Thành viên khác đã review; phản hồi được xử lý.
- [ ] Merge/đóng issue đúng quyền và đúng acceptance, evidence có URL thật.
- [ ] Kết luận và phần việc tiếp theo có trên GitHub, không chỉ trong chat.
