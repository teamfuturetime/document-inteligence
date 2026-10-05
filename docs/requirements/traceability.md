# Traceability matrix

Trạng thái chung: `planned`, `scaffolded`, `implemented`, `verified`, `blocked`. `verified` bên dưới chỉ chứng minh hành vi nền được nêu trong cột checks/evidence, không chứng minh hoàn thành cả yêu cầu PRODUCT_MVP. Đường dẫn code/test/evidence tương đối từ gốc repo.

| requirement_id | description | source | module | implementation_status | test_or_check | evidence_path | backlog_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MVP-01 | OCR | COURSE_REQUIRED | adapters/interfaces.py, fixture.py | scaffolded | Gate fixture, không gold leakage; engine thật chưa có | backend/tests/test_api.py; docs/reports/foundation-verification.md | BL-002/003 |
| MVP-02 | Schema extraction | COURSE_REQUIRED | domain/models.py, adapters | scaffolded | Types/evidence references; không kiểm chứng extraction thật | contracts/generated/ExtractionRun.schema.json | BL-001/004 |
| MVP-03 | Confidence trường | COURSE_REQUIRED | domain/Confidence | scaffolded | Unknown không chứa điểm; chưa calibration | backend/tests/test_domain.py; docs/ml/confidence-policy.md | BL-010 |
| MVP-04 | Review/sửa | COURSE_REQUIRED | frontend, domain/review.py | scaffolded | UI fixture chỉ xem; reviewed-null semantics | frontend/src/app/App.test.tsx; backend/tests/test_domain.py | BL-006 |
| MVP-05 | Validation | COURSE_REQUIRED | normalization.py, validation.py | verified | Unicode/zero/date/cross-field/draft; schema mẫu | backend/tests/test_domain.py | BL-001/006 |
| MVP-06 | Export JSON | COURSE_REQUIRED | ExportArtifact | scaffolded | Ví dụ/schema từ chối draft/invalid, chưa persisted export | contracts/examples/export-fixture.json; backend/tests/test_domain.py | BL-007 |
| DATA-01 | Synthetic/sample only | COURSE_REQUIRED | fixtures/manifest | verified | 6 mẫu tự render; checksum/source/font, đối chiếu ảnh | data/manifests/fixtures.json; docs/reports/foundation-verification.md | BL-008 |
| EVD-01 | Golden dataset | COURSE_REQUIRED | data | scaffolded | Seed contract, chưa golden benchmark đủ đại diện | docs/data/dataset-card.md; data/manifests/fixtures.json | BL-008 |
| EVD-02 | Field metrics | COURSE_REQUIRED | evaluation | verified | Correct/wrong/missing/extra/absent/unreadable/zero; 50/48/45 | backend/tests/test_evaluation.py; evaluation/reports/fixture-contract.json | BL-009 |
| EVD-03 | Error taxonomy | COURSE_REQUIRED | docs/ml, examples | implemented | Mã/record và ví dụ synthetic, chưa thống kê model | docs/ml/error-taxonomy.md; evaluation/examples/error-illustrative.json | BL-009 |
| EVD-04 | Versioning | COURSE_REQUIRED | config, RunManifest | verified | Run fixture có commit/dirty, versions/hashes, locks | contracts/generated/RunManifest.schema.json; evaluation/reports/fixture-contract-run.json | BL-009 |
| ENG-01 | Cài/chạy lại | FOUNDATION_REQUIRED | uv/npm, Docker | verified | Native Windows install/server/build; Docker chưa chạy | docs/reports/foundation-verification.md | BL-012 |
| ENG-02 | Issue/PR | FOUNDATION_REQUIRED | .github, docs/team | implemented | Templates local/check YAML/links; remote chưa cấu hình | .github/PULL_REQUEST_TEMPLATE.md; docs/governance/github-setup.md | BL-001/012 |
| ENG-03 | Tests/CI | FOUNDATION_REQUIRED | tests, ci.yml | verified | Checks local; Actions run chưa có evidence | docs/reports/foundation-verification.md | BL-012 |
| ENG-04 | Khả năng trung thực | FOUNDATION_REQUIRED | API/UI/docs | verified | ocr_ready false, 503 unconfigured, fixture banner/disabled UI | backend/tests/test_api.py; frontend/src/app/App.test.tsx | BL-012 |

NFR IDs nằm trong [SRS](srs.md); test plan ánh xạ các checks tương ứng. CI remote và container execution vẫn pending, không được suy diễn từ trạng thái verified của kiểm tra local.
