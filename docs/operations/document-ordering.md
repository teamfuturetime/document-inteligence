# Thứ tự tài liệu, lịch sử và queue — issue #46

Khi timestamp trùng nhau, thứ tự được xác định bằng ID duy nhất theo lexical order:

| Luồng | Thứ tự |
| --- | --- |
| Danh sách tài liệu | created_at DESC, document_id DESC |
| Danh sách runs trong history | created_at DESC, run_id DESC |
| Worker chọn queued run | created_at ASC, run_id ASC |
| Events trong history | event_id DESC (giữ nguyên) |

ID làm tie-breaker cố định, không phải insertion order hoặc số thứ tự thời gian. Worker không
sort random hay đổi scheduler; trong một nhóm queued cố định cùng timestamp, mỗi run được chọn
theo thứ tự ID một lần rồi rời nhóm queued. Timestamp vẫn là khóa ưu tiên đầu tiên. Không hứa
FIFO theo insertion order cho các records cùng timestamp, hoặc fairness khi đồng hồ/data bị
thay đổi đồng thời ngoài điều kiện kiểm này.

`documents.latest_run_id` vẫn là nguồn chuẩn của run hiện hành. Không chọn history[0] làm latest:
hai runs cùng timestamp có thể có run mới thực sự với ID thấp hơn. Giữ guards expected_run_id,
revision/status CAS, owner/status/type filters, immutable prediction/review/null và confirmed export.
Không đổi shape API/schema/version hoặc generated types; generator --check phải tiếp tục đạt.

Với dataset bất biến, limit/offset phân trang cho thứ tự ổn định, không trùng/thiếu ở ranh giới
các pages. Offset không phải snapshot khi có insert/delete/update concurrent; frontend giữ thứ
tự server, không sort lại bằng timestamp cục bộ. Restart và backup/restore giữ timestamp/ID nên
cùng dữ liệu cho cùng thứ tự, không phụ thuộc index/row insertion order.

Tests SQLite thật đóng băng clock và đảo thứ tự IDs/insertion: list/status/type/owner pagination,
queue processing qua cùng process/restart/backup restore và history/latest/confirm/export.
Component smoke điều khiển Trang sau/Trang trước trên 12 documents có cùng timestamp, kiểm
offset0→10→0 và không trùng/thiếu khi server trả thứ tự đã định nghĩa. Fetch/inference doubles
được khai báo rõ; không gọi component smoke là native browser hoặc benchmark accuracy.

## Nhánh phụ thuộc

#46 làm tuần tự trên nền PR #57 để giữ fix persistence cùng service. PR tạm nhắm
`fix/45-storage-failures`, chỉ chứa delta #46; giữ Draft đến khi nền được review/tích hợp.
Workflow thêm đúng target branch này để PR phụ thuộc vẫn chạy sáu jobs + Product checks;
không bỏ check hoặc thay protection. Sau nền vào main, đồng bộ/đổi base và chạy CI lại.
