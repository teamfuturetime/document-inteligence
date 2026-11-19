# Doctor chỉ đọc — issue #41

Trước chạy app sau clone/pull, dùng Python entry point từ repository root:

```sh
python scripts/dev.py doctor
python scripts/dev.py doctor --json --runtime runtime/app
```

Lệnh giống nhau trên Windows/POSIX (`python3` nếu máy dùng tên đó). Launcher chọn Python
trong `backend/.venv` nếu đã cài, nếu không dùng Python đang chạy. Không gọi `uv run`,
setup, tải models, sửa `.env`, tạo runtime/account hoặc migrate DB. Khi thiếu dependencies,
báo `dependencies_missing`; người vận hành chủ động chạy setup theo README rồi kiểm lại.
Các thao tác khắc phục trong output là hướng dẫn, không được doctor tự thực hiện.

Doctor dành cho **runtime offline, cây thư mục ổn định**. Dừng app/worker trước kiểm DB.
Nếu có SQLite WAL/journal, báo `offline_required`, không xóa/checkpoint hay bỏ qua file đó
để đọc DB. Để SQLite hoàn thành recovery/checkpoint qua quy trình vận hành bình thường;
không tự xóa sidecars. Probe dùng URI `mode=ro&immutable=1`, query-only và deadline SQL
3 giây, không khởi tạo repository/service/worker. Không dùng doctor để chứng minh readiness
của app đang chạy, không thay verifier backup (#42) hoặc security audit.

## Kết quả

JSON có `report_version: 1`, `status` và danh sách `checks`. Mỗi check có `name`, `status`,
`code`, `action`; phiên bản tool có `expected`/`observed` chỉ chứa số phiên bản.
Config chỉ xuất `auth_mode`/`provider_mode`; DB chỉ xuất schema version được nhận diện.
Không xuất paths, raw tool output/stderr, exception/validation input, tài khoản, session,
password hash, field hoặc ảnh nguồn. Không gửi telemetry/network requests từ doctor.

| Exit | Status | Ý nghĩa |
| --- | --- | --- |
| 0 | `ready` | Các probes đạt với pins/profile native và DB2 offline được nhận diện. |
| 1 | `action_required` | Thiếu/lệch tool/model, runtime chưa tạo/rỗng, DB1 cần xử lý, hoặc profile chưa native. |
| 2 | `error` | DB/schema không hợp lệ/tương lai, config sai, tool lỗi/timeout hoặc launcher lỗi. |

`ready` chỉ là kết quả các probes, không chạy OCR, không chứng nhận mọi asset/row hợp lệ.
Fixture được báo `fixture_only`/action required để không nhầm contract demo với native OCR.
Profile local/session được validate bằng Settings chuẩn, giữ default local; không kiểm/khai
tài khoản có tồn tại hoặc tự bật session. Origin/cookie sai chỉ báo config_invalid.

Các trạng thái runtime: `runtime_missing`, `runtime_empty`, `database_missing` (có files khác),
`database_empty` (file 0 bytes), `schema1_empty`, `migration_required` (DB1 có dữ liệu),
schema2 `ready`, `future_schema`, `database_invalid`, `offline_required`, `unreadable`.
DB được quick_check và kiểm cấu trúc tối thiểu; không đọc nội dung accounts/documents để in.
DB1 không bị upgrade. Backup/migration offline xem [runbook auth](auth-ownership.md).

Python/uv/Node/npm được so với pins trong Product CI; Tesseract cần major 5, models kiểm
hash theo lock hiện có. Probe tools có timeout 3 giây mỗi tool, toàn subprocess doctor
tối đa 30 giây; lỗi timeout trả error, không tiếp tục bằng fixture fallback. Doctor gọi
tools đã cài với `--version` (không shell) và đọc model files, không OCR hoặc cài tool.

## Kiểm chứng

```sh
uv run --project backend --locked pytest backend/tests/test_doctor.py -q
```

Tests dùng SQLite thật/schema1/schema2, snapshot bytes và danh sách files trước/sau,
tool doubles cho lỗi/timeout/phiên bản, model corrupt/missing và smoke entry point thật
trên runtime tạm. CI Windows chạy cùng suite; POSIX backend chạy toàn suite. Tool doubles
không phải chứng nhận tool thật/native OCR. Giữ Product gate và native/browser suites.
