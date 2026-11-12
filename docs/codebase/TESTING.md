# Testing Patterns

## 1) Test Stack and Commands
pytest9.1.1+httpx2 TestClient, Vitest5.0.3/Testing Library, Playwright Chromium. Root `python scripts/dev.py check` offline; `ocr` native HTTP; `e2e` real browser/native DB temporary. No coverage package/threshold claimed for selected platform; counts/results in ../consolidation-verification.md.

## 2) Test Layout
backend/tests: API/domain/SQLite/manifest/metrics/product; pipeline/tests: geometry/preprocess/parser/timeout/extraction. Frontend source component tests. Browser spec separate from Vitest. New retry tests copied byte-identically from 9a76a6e, attribution in source-lineage.

## 3) Test Scope Matrix
Unit: normalization/schema/evaluator/pipeline doubles. Integration: TestClient real SQLite/files and CAS/restart/reprocess/export. Native: verify_product requires Tesseract+models and fails missing readiness, both invoice/application. E2E: browser runs a dedicated native backend/runtime; no mocked extraction used. Auth tests not applicable to unauthenticated single-user app; must be added when porting ownership.

## 4) Mocking and Isolation Strategy
tmp_path runtime per test, monkeypatch provider/decode seams explicit. Worker disabled for deterministic workflow tests; native helper starts it. Frozen evaluator replay uses recorded native predictions, not new inference. No secret/provider network needed in PR jobs; model downloads only setup, never inference.

## 5) Coverage and Quality Signals
Risk assertions protect null/revision/authority/idempotency, not just HTTP/schema. Frozen regression compares full evaluator output to selected platform's stored report, checked against immutable test labels/membership. New native reports have own engine/config/source; Windows5.4 not assumed same as Linux/macOS. Small synthetic templates do not prove unseen invoice accuracy. Remote new workflow unverified until approved push.

## 6) Evidence
backend/tests/{test_product.py,test_async_retry_vt042.py,test_product_evaluation.py}; pipeline/tests/test_pipeline.py; scripts/{verify_product.py,check_evaluation_regression.py}; evaluation/runs/2026-10-24-test-frozen; ../consolidation-verification.md.
