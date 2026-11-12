# GitHub publication — consolidation

Chủ dự án đã duyệt gói thao tác sau khi xem nội dung local. Chỉ push nhánh consolidation, mở PR, tạo backlog và bảo vệ main sau CI; không ủy quyền merge/đóng PR #1/xóa refs.

## Nhánh và PR

- [chore/repository-consolidation](https://github.com/teamfuturetime/document-inteligence/tree/chore/repository-consolidation), original published head `d597eb5127d0258969d207ec77dd1ad988c9fe6c`.
- [PR #3 → main](https://github.com/teamfuturetime/document-inteligence/pull/3), giữ original nhatquang ancestry và attribution; chưa merge.
- [PR #1](https://github.com/teamfuturetime/document-inteligence/pull/1) vẫn mở, không tự đóng; [PR #2](https://github.com/teamfuturetime/document-inteligence/pull/2) vẫn là merge autosave vào minhthao.

## Backlog đã tạo

| Local ID | GitHub Issue |
|---|---|
| CONS-01 | [#4 - Đưa nền OCR hóa đơn local đã kiểm chứng vào main](https://github.com/teamfuturetime/document-inteligence/issues/4) |
| CONS-02 | [#5 - Review chéo nhãn và provenance của baseline nền chính](https://github.com/teamfuturetime/document-inteligence/issues/5) |
| CONS-03 | [#6 - Port PDF một trang vào pipeline chính với giới hạn tài nguyên](https://github.com/teamfuturetime/document-inteligence/issues/6) |
| CONS-04 | [#7 - Port autosave vào field review có CAS và conflict UI](https://github.com/teamfuturetime/document-inteligence/issues/7) |
| CONS-05 | [#8 - Giới hạn receive/admission cho upload chậm và lớn](https://github.com/teamfuturetime/document-inteligence/issues/8) |
| CONS-06 | [#9 - Triage dependency audit trước mở rộng deployment](https://github.com/teamfuturetime/document-inteligence/issues/9) |
| CONS-07 | [#10 - Thêm notification sau persisted business event, tách lỗi gửi](https://github.com/teamfuturetime/document-inteligence/issues/10) |
| CONS-08 | [#11 - Thiết kế port auth/ownership khi cần nhiều người dùng](https://github.com/teamfuturetime/document-inteligence/issues/11) |
| CONS-09 | [#12 - Đánh giá policy và các loại tài liệu mở rộng trước khi port](https://github.com/teamfuturetime/document-inteligence/issues/12) |

Đã tạo8 labels trong `.github/consolidation/labels.json`; không sửa/xóa labels cũ hoặc gán người phụ trách. Ba milestones không due date:
- [M1 - Nền OCR local dùng chung](https://github.com/teamfuturetime/document-inteligence/milestone/1)
- [M2 - Định dạng và review mở rộng](https://github.com/teamfuturetime/document-inteligence/milestone/2)
- [M3 - Quyền truy cập và tích hợp tùy chọn](https://github.com/teamfuturetime/document-inteligence/milestone/3)

## CI và bảo vệ main

Trạng thái được xác minh tại 2026-11-12T10:59:40.729740+00:00:

- [Push run43204361810](https://github.com/teamfuturetime/document-inteligence/actions/runs/43204361810) và [PR run43204531017](https://github.com/teamfuturetime/document-inteligence/actions/runs/43204531017) đều **success**, head `d597eb5127d0258969d207ec77dd1ad988c9fe6c`. Backend checks, Frontend checks, Evaluation regression, OCR integration, Browser E2E và Product checks đều đạt. Đây là evidence remote thực, không suy từ YAML hoặc check của baseline cũ.
- PUT và GET main protection đã xác minh: required context `Product checks`, strict=true, cần1 review + last-push approval, dismiss stale reviews, enforce admins, resolve conversations; không bắt CODEOWNERS, không ép linear history; force-push/delete bị cấm.
- Main vẫn `94c5101`, PR#3 chưa merge và PR#1 còn mở. Việc bảo vệ main không đưa ứng dụng lên main; nhóm phải review PR#3 trước. Không auto-merge hoặc tự approve.
- [Snapshot máy đọc được](evidence/github-publication.json) ghi operation IDs/URLs/check names/settings. [PR checks hiện tại](https://github.com/teamfuturetime/document-inteligence/pull/3/checks) là nơi kiểm SHA mới nhất sau các commit docs tiếp theo; các run cố định trên là bằng chứng tại lần publish đầu.

Các tài liệu audit/baseline trước đây ghi trạng thái trước khi chủ dự án duyệt, được giữ đúng mốc thời gian. `.github/consolidation/*.json` là nội dung gói đã duyệt và nguồn tái kiểm tra, không được tự áp lại khi chưa có yêu cầu.
