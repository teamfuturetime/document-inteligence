# Health và runtime readiness — issue #48

App0.5.0 thêm `GET /api/v1/readiness` cho consumer frontend (#50) và người vận hành.
`GET /api/v1/health` giữ nguyên shape/status liveness: app trả lời HTTP không chứng minh OCR
đã sẵn sàng. Readiness200/status `ready` khi lifecycle running, DB schema2 truy cập được,
worker thread còn sống/chưa stop và native provider đạt probe startup; còn lại503/not_ready.
Cả200/503 dùng backend domain Readiness, OpenAPI/generated TS/examples cùng nguồn chuẩn.
Không đổi SQLite schema2 hoặc export1.0.0; default local vẫn giữ nguyên.

| Field | Các trạng thái |
| --- | --- |
| lifecycle | not_started, starting, running, stopping, stopped |
| database | not_checked, ready, unavailable, unsupported_schema |
| worker | not_started, disabled, ready, stopped |
| provider | not_checked, ready, unconfigured, fixture, unavailable |
| provider_check | startup_snapshot |
| provider_mode | unconfigured, fixture, tesseract |
| auth_mode | local, session |

Response còn có app_version/status; không có paths/SQL/user/session/document counts, token,
ảnh hoặc field. Endpoint được phép đọc anonymous như health trong local/session mode,
không thay authentication cho tài liệu; response `Cache-Control: no-store`.

**Provider là snapshot lúc startup**, không khẳng định tool/models chưa bị thay đổi sau đó.
Probe một lần, chỉ kiểm hashes đã pin và engine version, timeout process3s, không OCR hoặc
download. Poll không gọi lại capabilities/probe hoặc đọc/hash models. Nếu môi trường OCR
đổi sau startup, kiểm capabilities/doctor theo runbook và khởi động lại để làm mới snapshot;
không coi cached provider field là monitor liên tục hay kết quả accuracy.

Mỗi poll chỉ đọc version SQLite hiện có bằng URI `mode=ro`, không tạo DB thiếu/initialize/
migrate/integrity scan, connect timeout50ms và progress budget100ms; SQL/OS errors trả mã
trạng thái an toàn. Không lấy counts hoặc resource theo owner. Kiểm worker qua is_alive/stop
trong memory, không khởi động worker mới. Trước startup/trong shutdown không đọc DB.
Đây là các budget cục bộ, không cam kết latency/SLA toàn HTTP khi server/OS quá tải.

Fixture/unconfigured không đủ điều kiện xử lý OCR sản phẩm nên readiness503 dù health200;
fixture catalog vẫn dùng được. start_worker=False trong harness → worker not_started/503
ở profile tesseract. DB mất/hỏng → unavailable, schema khác2 → unsupported_schema; không
tự phục hồi/migrate. Worker stopped hoặc lifecycle stopping/stopped cũng trả503.

Consumer #50 nên phân biệt HTTP503 có Readiness body với mất kết nối/network errors; không
parse body theo ErrorEnvelope trong trường hợp readiness503. Dừng/pause thao tác cần backend
khi chưa ready và đối chiếu session/resource trước tiếp tục; không tự replay writes hoặc
chuyển recovery draft giữa accounts. Không poll OCR/capabilities liên tục để thay readiness.

## Kiểm chứng

```sh
uv run --project backend --locked pytest backend/tests/test_readiness.py -q
```

Tests dùng SQLite thật, native worker thread thật nhưng process_next/probe doubles tường minh:
chưa startup/đã shutdown không tạo DB, profile local/session và fixture/unconfigured, DB mất/
hỏng/schema tương lai/lock-recovery, worker dừng, repeated polls không initialize/hash models,
không lộ canary/paths, OpenAPI503 đúng model. Không gọi đây là native OCR test. CI giữ native
local/session/browser và thêm readiness suite vào Windows job hiện có, gate không giảm.
