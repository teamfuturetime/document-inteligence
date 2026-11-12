# Diễn giải lỗi HTTP và profile đối chứng - 12/11/2026

## Lượt người dùng gửi

`user-cold-176.json`: 176/200 tác vụ thành công, 24 lỗi, 1.056/1.200 response.
Task p95 0.951530s dưới 5s nhưng `correctness_pass=false` và `acceptance_pass=false`.
Các tác vụ lỗi chưa nhận được response nào. Raw errors gồm 22
ConnectionResetError, một BrokenPipeError và một OSError(22) ở TCP_NODELAY.

Đây là kết quả thật cần giữ trong evidence. p95 có cả các tác vụ dừng sớm và
khối lượng công việc hoàn tất bị thiếu, nên không được dùng để tuyên bố đạt.
Postcondition dữ liệu còn nguyên không chứng minh 24 tác vụ đã hoàn tất.

## Điều đã kiểm tra

- macOS báo `kern.ipc.somaxconn=128`; FD soft limit là 1.048.575. Hàng đợi TCP
  là một giả thuyết nhưng số liệu này không chứng minh nguyên nhân root cause.
- Thử asyncio/h11 hoặc asyncio/auto có lượt qua, nhưng khi lặp asyncio/auto
  vẫn có một lượt 190/200. Không nhận đó là bản sửa đáng tin cậy.
- Tách server sang spawned process riêng cũng vẫn lỗi (131/200, 176/200,
  179/200). Refactor process và thay loop mặc định đều được loại bỏ.
- Một script thử nghiệm bị nhầm tham số không khởi động được server; log đó
  được giữ riêng là lỗi setup, không được tính thành số đo tải.
- Không thay sysctl, không retry, không giảm số tác vụ và không sửa nghiệp vụ.

Kết luận giới hạn: sự cố xuất hiện ở ranh giới TCP/HTTP khi phát đợt kết nối
mới; chưa chứng minh được nguyên nhân chính xác là OS, event loop, server,
hàng đợi hoặc môi trường chạy. Không gọi đây là lỗi đã được sửa ở production.

## Hai profile rõ ràng

| Profile | Chuẩn bị | Workload đo | Diễn giải |
|---|---|---|---|
| `cold` (mặc định) | Không chuẩn bị connection | 200 tác vụ mở kết nối mới cùng lúc, mỗi tác vụ 6 bước; tính cả connect/scheduling | Giữ nguyên lượt người dùng gửi; còn lỗi kết nối |
| `preconnected` (tùy chọn) | 200 GET hợp lệ tạo 200 connection riêng; ghi riêng timing/records | Barrier vẫn phát 200 tác vụ đồng thời, mỗi tác vụ cùng 6 bước và assertions; không retry | Đo API workload của 200 client đã kết nối; không đo cold connection capacity |

Các lượt CLI của code cuối:

| Lượt preconnected | Setup GET | Request đo hợp lệ | Tác vụ thành công | p95 tác vụ |
|---|---|---|---|---|
| 1 | 200, 0.198s | 1.200/1.200 | 200/200, 0 lỗi | 1.336765s |
| 2 | 200, 0.162s | 1.200/1.200 | 200/200, 0 lỗi | 1.170992s |
| 3 | 200, 0.165s | 1.200/1.200 | 200/200, 0 lỗi | 1.128449s |

Mỗi lượt tổng cộng 1.400 request gồm 200 setup + 1.200 đo. Setup không tính vào
task latency, được khai báo `setup_in_task_latency=false`; raw setup records
được lưu riêng. Đọc `connection_mode` và `scope` cùng kết quả p95.

Lượt kiểm tra lại default cold vẫn lỗi: 129/200, 71 lỗi. Log này cũng được giữ,
không chọn bỏ chỉ vì profile preconnected đã qua. Regression sau patch:
133 passed, 6 deprecation warnings. Implementation lifecycle và dữ liệu giả
không thay đổi; patch chỉ thêm một profile có scope công khai vào driver.

## Chạy lại trên đúng máy hiện tại

```bash
cd /Users/nguyencongtri/Documents/SE/bt3-vt044
source ../document-inteligence/.venv312/bin/activate
PYTHONPATH=backend:. python -m individual.VT044.load --transport stdlib --connection-mode preconnected --output ../output/BT3_23001945_tu_chay/load-http-preconnected.json
```

Để lặp đúng lượt cold trước đây, bỏ `--connection-mode preconnected` hoặc ghi
`--connection-mode cold`; dùng tên output khác để giữ dữ liệu cũ. Không cần
`git pull` trên worktree chung này: source hiện tại đã được cập nhật trực tiếp.

Raw evidence đầy đủ: `evidence/http-diagnostics/`; kế hoạch trước các thay đổi
và các giả thuyết bị bác bỏ nằm trong `LOAD_FIX_PLAN.md`.
