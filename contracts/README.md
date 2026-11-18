# Nguồn chuẩn hợp đồng

App **0.4.0** thêm session opt-in theo [ADR0011](../docs/decisions/0011-authentication-ownership.md).
`docintel.domain.auth` là nguồn Credentials/UserIdentity/SessionState; schema và types được sinh cùng generator.
`GET /auth/session` trả mode và user/CSRF hiện hành; không trả cookie token hoặc password/hash.
Session mode yêu cầu cookie HttpOnly cho product endpoints và `X-CSRF-Token` cho POST/PUT;
login yêu cầu JSON, `X-Requested-With: docintel` và Origin chính xác.
Local mode giữ namespace reserved `local`. 401 là phiên thiếu/hết hạn, 403 là origin/CSRF sai,
404 dùng chung cho tài liệu không tồn tại/khác owner. Không retry write tự động khi đổi phiên.
Examples `session-local.json`/`session-anonymous.json` không chứa tài khoản mặc định hoặc secret.
SQLite schema 2 cần offline migration cho runtime schema 1 có dữ liệu; export schema 1.0.0 giữ nguyên.

App 0.2.0 bổ sung nguồn chuẩn `docintel.domain.documents`: invoice/application workflow, review requests, history và persisted export. Product schema 1.0.0 sinh cùng generator; không đổi nghĩa foundation fixture schema 1.0.0. `pipeline.models` chỉ là DTO implementation được adapter chuyển sang backend domain, không nguồn HTTP thứ hai.

App 0.2.1 bổ sung receive/admission budget cho upload và OpenAPI lỗi 400/408; envelope lỗi và product/export schema giữ nguyên. [Chi tiết lỗi, retry và budget](../docs/operations/upload-ingress.md).

Domain models backend và FastAPI là nguồn chuẩn. `generated/*.schema.json` (JSON Schema 2020-12) và `generated/openapi.json` được sinh bằng:

```powershell
uv run --project backend --locked python scripts/generate_contracts.py
npm --prefix frontend run contracts:generate
```

CI dùng `--check` và `npm --prefix frontend run contracts:check` so sánh nội dung, fail nếu drift. Script frontend sinh `src/lib/api.generated.ts` qua openapi-typescript; API client dùng types này. Không sửa bản sinh bằng tay. Business validators/test là nguồn quy tắc lịch và liên trường mà JSON Schema cấu trúc không diễn đạt hết.

Examples: `fixture-view.json` response thật của adapter fixture; `export-fixture.json` **minh họa trạng thái confirmed**, không có reviewer/persistence thật; `draft-invalid.json` hợp lệ với draft nhưng chưa đạt bản cuối; `error-unavailable.json` envelope lỗi minh họa. Foundation chưa có request upload/review, nên không tạo payload endpoint giả.

Sinh lại examples sau đổi fixtures bằng `uv run --project backend --locked python scripts/generate_examples.py`. Export schema 1.0.0 độc lập app 0.1.0; quy tắc breaking/version ở [data contracts](../docs/architecture/data-contracts.md).
