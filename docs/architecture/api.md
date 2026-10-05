# API

## Đã chạy trong foundation

| Method/path | Response | Ghi chú |
| --- | --- | --- |
| GET /api/v1/health | Health 200 | Tiến trình/version; không OCR readiness |
| GET /api/v1/capabilities | Capabilities 200 | mode, schemas, feature statuses, ocr_ready=false, model not_measured |
| GET /api/v1/schemas | SchemaInfo[] 200 | Đơn đề nghị provisional |
| GET /api/v1/fixtures | FixtureCatalog 200/503 | Chỉ khi explicit fixture mode |
| GET /api/v1/fixtures/{sample_id} | FixtureView 200/404/503 | Fixture source, draft/issues, image_url |
| GET /api/v1/fixtures/{sample_id}/image | PNG 200/404/503 | ID từ manifest, không nhận path tùy ý |

Nguồn chuẩn response trong [OpenAPI](../../contracts/generated/openapi.json). Lỗi envelope: `{"error":{"code":"PROVIDER_UNAVAILABLE","message":"…","request_id":"…"}}`, có X-Request-ID do server sinh. Không trả 200 để che lỗi; không gửi stack/path nội bộ. Không có route upload/export giả.

## API mục tiêu — planned

| Method/path | Request/response đề xuất | Lỗi và retry |
| --- | --- | --- |
| POST /api/v1/documents | multipart file + document_type; 201 Document | 413 FILE_TOO_LARGE; 415 UNSUPPORTED_FILE; 422 IMAGE_LIMIT/SCHEMA_NOT_FOUND; sửa input trước retry |
| POST /api/v1/documents/{id}/runs | schema/config version + idempotency_key; 202 run_id/status_url | 404 DOCUMENT_NOT_FOUND; 503 PROVIDER_UNAVAILABLE; key lặp cùng payload trả run cũ, khác payload 409 |
| GET /api/v1/runs/{run_id} | 200 pending/running/succeeded/failed/unavailable + typed failure | 404; poll backoff; failed không trả prediction thành công giả |
| GET /api/v1/runs/{run_id}/predictions | 200 ExtractionRun khi succeeded | 409 RUN_NOT_COMPLETE; 503 provider unavailable nếu chưa có run |
| PUT /api/v1/documents/{id}/revisions | run_id, expected_revision, reviewed fields; 201 ReviewRevision + issues | 409 REVISION_CONFLICT; draft invalid vẫn lưu kèm issues; retry cùng key có semantics chốt BL-006 |
| POST /api/v1/documents/{id}/revisions/{revision}/confirm | expected_revision, warning_ack_codes; 200 persisted confirmed revision | 409 REVISION_CONFLICT; 422 VALIDATION_FAILED; retry idempotent với cùng revision |
| GET /api/v1/documents/{id}/revisions/{revision}/export | Không nhận dữ liệu cuối từ client; 200 ExportArtifact | 409 EXPORT_STALE/NOT_CONFIRMED; 422 VALIDATION_FAILED; 404 revision; retry đọc cùng artifact |

Mã xử lý PROVIDER_FAILURE/TIMEOUT/QUOTA được lưu run status và thông điệp an toàn; HTTP 503 cho unavailable, 502 provider failed khi synchronous, 504 timeout nếu request chờ. Retry provider có giới hạn và không fallback mock. Async sơ bộ vì OCR có thể dài; BL-005 chốt worker local/recovery sau đo baseline. Các request/response mục tiêu phải được đưa vào OpenAPI khi triển khai, không duy trì spec hand-written song song đang hoạt động.
