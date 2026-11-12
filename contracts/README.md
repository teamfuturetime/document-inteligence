# Nguồn chuẩn hợp đồng

App 0.2.0 bổ sung nguồn chuẩn `docintel.domain.documents`: invoice/application workflow, review requests, history và persisted export. Product schema 1.0.0 sinh cùng generator; không đổi nghĩa foundation fixture schema 1.0.0. `pipeline.models` chỉ là DTO implementation được adapter chuyển sang backend domain, không nguồn HTTP thứ hai.

Domain models backend và FastAPI là nguồn chuẩn. `generated/*.schema.json` (JSON Schema 2020-12) và `generated/openapi.json` được sinh bằng:

```powershell
uv run --project backend --locked python scripts/generate_contracts.py
npm --prefix frontend run contracts:generate
```

CI dùng `--check` và `npm --prefix frontend run contracts:check` so sánh nội dung, fail nếu drift. Script frontend sinh `src/lib/api.generated.ts` qua openapi-typescript; API client dùng types này. Không sửa bản sinh bằng tay. Business validators/test là nguồn quy tắc lịch và liên trường mà JSON Schema cấu trúc không diễn đạt hết.

Examples: `fixture-view.json` response thật của adapter fixture; `export-fixture.json` **minh họa trạng thái confirmed**, không có reviewer/persistence thật; `draft-invalid.json` hợp lệ với draft nhưng chưa đạt bản cuối; `error-unavailable.json` envelope lỗi minh họa. Foundation chưa có request upload/review, nên không tạo payload endpoint giả.

Sinh lại examples sau đổi fixtures bằng `uv run --project backend --locked python scripts/generate_examples.py`. Export schema 1.0.0 độc lập app 0.1.0; quy tắc breaking/version ở [data contracts](../docs/architecture/data-contracts.md).
