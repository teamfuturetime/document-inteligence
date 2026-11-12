# Product traceability trên nhatquang — 24/10/2026

Trạng thái dưới đây dành cho candidate local 0.2.0, không thay bảng foundation lịch sử hoặc xác nhận giảng viên/nhóm đã nghiệm thu. Verified chỉ áp dụng checks/evidence đã chỉ ra; remote CI/Docker và review nhãn bởi nhóm còn pending.

| requirement_id | description | source | module | implementation_status | test_or_check | evidence_path | backlog_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MVP-01 | OCR thật vie+eng | COURSE_REQUIRED | pipeline/tesseract, image worker | verified local | Native OCR/timeout/model-hash/geometry tests | evaluation/reports/product-native-2026-10-24.json | BL-002/003 |
| MVP-02 | Trích xuất theo schema, evidence | COURSE_REQUIRED | pipeline/extraction, domain/documents, adapter | verified local | 5 invoice/7 application fields, ambiguity/null/evidence checks | evaluation/runs/2026-10-24-test-frozen/report.json | BL-001/004 |
| MVP-03 | Confidence và abstention | COURSE_REQUIRED | PipelineConfig, confidence policy 1.1.0 | verified on validation | Policy grid trên validation, low-score null giữ evidence; không calibrated | evaluation/reports/confidence-selection-2026-10-24.json | BL-010 |
| MVP-04 | Review/sửa/lưu/reload | COURSE_REQUIRED | DocumentService, ReviewPanel | verified local | Explicit-null, hai clients CAS, dirty/conflict UI, restart/reprocess | backend/tests/test_product.py; frontend/src/features/documents/ReviewPanel.test.tsx | BL-005/006 |
| MVP-05 | Validation draft/final | COURSE_REQUIRED | domain/documents | verified local | Invalid draft lưu được; confirm invalid/missing chặn; calendar/types/zero | backend/tests/test_product.py; pipeline/tests/test_pipeline.py | BL-001/006 |
| MVP-06 | Server export đúng revision | COURSE_REQUIRED | services/documents.export, API route | verified local | Stale/unconfirmed/approved injection bị từ chối, browser download thực | contracts/examples/product-export-synthetic.json | BL-007 |
| DATA-01 | Synthetic/sample only | COURSE_REQUIRED | API/input provenance, generators | verified for bundled data | Synthetic marker/nguồn/font hashes, không file font/models/DB trong Git | data/manifests/product.json | BL-008 |
| EVD-01 | Golden dataset | COURSE_REQUIRED | data/product, manifests | implemented; group review pending | 150 parents, hashes/splits/types/bounds; chưa giả review chéo đủ nhãn | data/product/README.md | BL-008 |
| EVD-02 | Field metrics | COURSE_REQUIRED | evaluation/product | verified on reported runs | TP/FP/FN, present/readable, absent/unreadable, support/exclusions, zero denominator | backend/tests/test_product_evaluation.py; evaluation/runs/2026-10-24-test-frozen | BL-009 |
| EVD-03 | Error taxonomy | COURSE_REQUIRED | evaluation error records, docs/ml | verified on development errors | Agent đối chiếu ảnh/OCR cho 5 lỗi trên 4 documents; lỗi còn mở, group review pending | evaluation/reports/error-triage-2026-10-24.json | BL-009 |
| EVD-04 | Model/config/run versions | COURSE_REQUIRED | pipeline/provenance, release manifest | verified local | Pinned weights, config/rules/source hashes, actual Git dirty/runtime | evaluation/reports/product-candidate-2026-10-24.json | BL-009 |
| ENG-01 | Cài/chạy lại | FOUNDATION_REQUIRED | uv/npm, runbook, backup | verified native; Docker pending | Native Windows/browser, lockfiles, backup/restore; chưa container execution | docs/reports/product-verification-2026-10-24.md | BL-012 |
| ENG-02 | Cộng tác issue/PR | FOUNDATION_REQUIRED | handoff, existing templates | implemented local | Branch nhatquang, source lineage; không bịa remote PR/review | docs/product/integration-handoff.md | BL-001/012 |
| ENG-03 | Checks/CI | FOUNDATION_REQUIRED | Python/frontend tests, CI YAML | verified local; remote pending | 72 Python tests, 7 UI tests, native 14 checks, contracts/build/lint | docs/reports/product-verification-2026-10-24.md | BL-012 |
| ENG-04 | Capability trung thực | FOUNDATION_REQUIRED | capabilities/UI/provenance | verified local | Provider unavailable không fallback, fixture tách model, score không probability | backend/tests/test_api.py; docs/reports/product-verification-2026-10-24.md | BL-012 |
