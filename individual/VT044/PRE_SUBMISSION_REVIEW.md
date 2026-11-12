# Xử lý nhận xét trước nộp - 11/11/2026

## Bốn vấn đề trong nhận xét

| Vấn đề | Việc đã thực hiện | Evidence/kết luận |
|---|---|---|
| GitHub/URL chưa được xác minh | Clone mới từ remote; kiểm tra SHA, ancestry và 15 file; hiển thị nguyên URL branch và README ở trang đầu | `REMOTE_AUDIT.md`, `evidence/remote-audit/inventory.json`. Nhánh tồn tại; chưa chứng minh quyền đọc của người chấm vì truy cập ẩn danh trả 404. |
| Cam kết còn ở dạng nháp | Hỏi sinh viên về việc tự đọc/hiểu harness, test, reflection và nhận cam kết; nhận phản hồi thực tế rồi mới đổi trang đầu | Sinh viên: “Đã rà soát, hiểu và xác nhận cam kết”; `evidence/student-review.md`. |
| Harness chưa tích hợp production | Giữ nguyên phạm vi được đề cho phép; làm rõ phần dùng code thật, phần mới và fixture demo | `REVIEW_GUIDE.md`, mục 1/3.6/4.5 trong báo cáo đã sắp theo đề. Không tuyên bố production feature đã hoàn tất. |
| Chỉ có lời mô tả evidence | Chạy RED đúng commit và GREEN/mutation/coverage/order/load từ clone GitHub mới; giữ raw logs riêng | RED 21 fail/7 pass; GREEN 133 pass; mutant killed; harness 93/93 lines, 18/18 branches. |

## Checklist bàn giao

- [x] Xác minh nhánh có thật cùng README, test, patch, log và lịch sử commit.
- [x] Chạy lại các lệnh từ bản clone GitHub mới trên máy local; không gọi đó là
  chứng nhận CI hoặc review độc lập bởi người khác.
- [x] Sinh viên xác nhận tự rà soát code/test/reflection và nhận cam kết.
- [x] Xuất PDF, render và kiểm tra đủ 8 trang chính + 2 trang phụ lục; reflection
  324 từ; URL branch hiển thị đầy đủ và có hyperlink.
- [x] Tên file đúng: `BT3_23001945_VT-044.pdf`.
- [ ] Xác nhận giảng viên/người chấm mở được repository bằng tài khoản của họ.
  Git clone trong phiên này thành công, nhưng API không đăng nhập trả 404.
- [ ] Sinh viên tự nộp PDF và link branch vào Google Classroom. Chưa có merge
  hoặc team review; không khai nhận đã nộp.

Bản DOCX được nhắc trong nhận xét không có trong workspace. Các thay đổi áp
dụng cho bản Markdown/PDF thực tế; không khẳng định đã sửa/kiểm tra DOCX đó.

## Cập nhật thứ tự theo yêu cầu ngày 12/11/2026

Báo cáo gộp về đúng 5 nhóm của đề thay vì 8 nhóm riêng, có 23 tiểu mục đi theo
từng gạch đầu dòng. Pagination vẫn 8 trang chính + Phụ lục A/B; không thay thứ
tự thực nghiệm lịch sử. Mục 4.5 bổ sung cold/preconnected cùng setup exclusions;
5.1 truy vết tới C_LOAD, Phụ lục A ghi thêm đợt chẩn đoán tương ứng.
