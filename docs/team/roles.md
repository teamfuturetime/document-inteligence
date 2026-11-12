# Vai trò và nhận việc hiện hành

Nhóm trưởng đã phân công năm thành viên tại [issue #15](https://github.com/teamfuturetime/document-inteligence/issues/15). Assignees và trao đổi trên từng issue là nguồn tiến độ hiện hành; bảng này mô tả trách nhiệm, không thay cho xác nhận nhận việc của thành viên.

| Thành viên / GitHub | Trách nhiệm chính | Phạm vi issue | Review/phối hợp |
|---|---|---|---|
| Tùng — `canhtungdz` | Quản lý phạm vi, điều phối, dependency, tích hợp và tài liệu nhóm | #15 điều phối; #19 bàn giao tài liệu; #4/#13/#9 đã hoàn tất qua PR #3/#14/#17 | Review OCR/backend; PR do Tùng viết cần người khác duyệt |
| Quang — `NhatquangPham` | OCR/preprocessing/extraction, PDF và version/evidence | #6 PDF; #12 mở rộng để sau | Tùng review; phối hợp dữ liệu với Tuấn, UI với Thao |
| Trí — `congtri2103` | Backend, upload, persistence và contract | #8 ingress; #10 notification; #11 auth/ownership khi được chốt phạm vi | Tùng review; Thao review phần API/UI liên quan |
| Thao — `thao-181` | Frontend/review, autosave và xử lý xung đột | #7 autosave | Trí review contract/CAS; Tuấn nghiệm thu browser |
| Tuấn — `tuanqtb123-creator` | Dữ liệu, review nhãn độc lập và nghiệm thu | #5 nhãn/splits/provenance; phối hợp QA cho các PR tính năng | Tùng review; Quang giải thích nguồn, không thay review độc lập |

`nguyenbs` là người quan sát theo xác nhận của nhóm trưởng, không thuộc năm thành viên thực hiện; không giao task hoặc request review theo phân công này. Các handles đã đối chiếu danh sách collaborators, nhưng tài liệu không tự sửa quyền hay tạo CODEOWNERS.

Mỗi người giữ một task chính đang làm và phối hợp review khi phù hợp. Chủ tính năng tự viết tests và docs cho phần mình; Tuấn không test thay cả nhóm. Reviewer tự đọc và gửi review bằng tài khoản của mình, không approve hình thức. Xem [hướng dẫn nhận việc](github-collaboration.md) trước khi bắt đầu; cập nhật blocked/dependency và kế hoạch trên issue thay vì chỉ trong chat.

#10 đã có PR #18 để review; không còn là mục hoàn toàn chưa bắt đầu. #11/#12 vẫn cần chốt phạm vi trước khi thực hiện; không tự đổi DB, tích hợp provider hay triển khai public. Trạng thái PR/CI có thể thay đổi, xem GitHub để kiểm tra SHA mới nhất.

## Tài liệu lịch sử

Phân vai/ước lượng thời gian tại [kế hoạch 20/10](../planning/team-delivery-plan-2026-10-20.md) và [handoff sản phẩm nhatquang](../product/integration-handoff.md) giữ bối cảnh lúc viết. Không dùng các deadline, nhánh cá nhân hoặc sở trường đề xuất trong đó để thay phân công hiện hành.
