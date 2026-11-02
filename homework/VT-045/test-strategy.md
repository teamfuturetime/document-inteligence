# Risk-based contract testing - VT-045

Contract testing here checks an in-process provider (normalization + validation)
against a consumer-owned oracle derived from R05 and AC1-AC5, plus the homework
HTTP adapter. This is not Pact-based distributed consumer-driven verification.
The existing pipeline is also a consumer: extraction `succeeded` may coexist
with validation `valid=false`. HTTP 200 similarly does not prove valid business data.

## Portfolio and omitted tests
- Unit: strict policy types/version/range, inclusive boundaries, missing/duplicate
  config, immutable snapshots. Fast, deterministic; no dependency mocks except a
  targeted permission error and forbidden clock/random/network calls.
- Integration: actual temporary JSON files -> loader -> existing normalization
  and validation -> canonical serialization; existing fake-provider pipeline.
- API: TestClient checks full `ValidationResult`, business 200 rejection, and
  config 503 with an exact error-only payload. No assertion is status-only.
- Executable E2E harness: real loopback HTTP client -> Uvicorn -> synchronous
  service -> file -> normalization -> validation -> JSON -> outcome oracle, in
  the 100-task experiment. This is the smallest runnable service slice allowed
  by the assignment, not browser/product E2E.
- Omit browser upload/review/export E2E: no corresponding functionality at
  baseline. Omit VLM throughput/accuracy and external-service mocks: no VLM in
  this slice. Existing OCR tests run in regression but don't establish VLM quality.

## Data selection
Synthetic Vietnamese invoice, fixed ID `0000123`, date `03/04/2026`, seller
`Cửa hàng Mây Việt`, amount `125.000 ₫`, explicit locale vi-VN. Expected values
are independently written literals, not calculated by the function under test.
No personal records, real invoice or network fixture. Integer boundary fixtures
explicitly carry VND because integers contain no currency-suffix evidence.
Policy partitions: valid [0, safe integer], wrong type (bool/string/float), wrong
version, unknown/missing/duplicate keys, unreadable/malformed JSON. Amount
boundaries: 0, M-1, M, M+1, schema ceiling and ceiling+1. Business rejection and
configuration outage are different contracts and must not share success payloads.

## Test cases
`T` below = backend/tests/test_invoice_policy.py; functions use `test_tcNN_`.

| ID | Requirement/risk | Level | Precondition / input | Expected result | Priority |
|---|---|---|---|---|---|
| TC01 | AC1/AC5 default compatibility | integration | shipped JSON; amount=9007199254740991 | valid; amount intact; exactly four envelope keys | P0 |
| TC02 | AC2 ignored/stale config | integration | same process; 200000 -> 100000; amount125000 | pass -> invalid; null amount; exact policy error | P0 |
| TC03 | AC3 off-by-one/outcome | unit+integration | M=100000; 0,99999,100000,100001 | first three valid; last rejected; other fields/input unchanged | P0 |
| TC04 | AC1/AC4 unsafe config (negative) | unit+integration | 11 malformed/type/version/duplicate/extra cases | InvoicePolicyError; never default | P0 |
| TC05 | AC4 swallowed exception (failure path) | integration | missing file; injected PermissionError | sanitized InvoicePolicyError | P0 |
| TC06 | AC5 old rules (negative) | integration | USD, comma amount, -1, safe ceiling+1 | original field error; no invented successful value | P0 |
| TC07 | AC3/AC5 aliasing/schema | integration/contract | policy rejection; mutate returned seller | JSON round-trip exact; source and next result intact | P1 |
| TC08 | AC1/AC2 stale/shared snapshot | unit | loaded M=0, attempt assign, replace file | snapshot immutable; fresh load sees new ceiling | P1 |
| TC09 | AC3/AC4 status-only oracle | API/contract | reject -> accept -> corrupt JSON | 200+exact invalid outcome; 200+exact values;503+error only | P0 |
| TC10 | NFC1 order/concurrency | integration | two files;100 alternating calls;20 threads; reverse order | each outcome follows its own policy; no contamination | P1 |
| TC11 | NFC1 flaky time/environment | unit/integration | block clock/sleep/random/network; change CWD | identical deterministic serialized results | P1 |
| TC12 | AC3 multiple errors/zero | integration | M=0; amount0 then amount1+USD | zero valid; two independent errors, both fields null | P1 |
| TC13 | AC3/AC5 current consumer | pipeline contract | fake extraction125000; M100000 | extraction succeeded AND validation invalid with field error | P0 |
| PERF01 | NFC2 latency + status-only risk | HTTP harness E2E | 3 rounds x100 tasks; M100000;50x99999+50x100001 | every full outcome correct; each p95 <=3s; errors retained | P0 |

TC01-TC13 expand to 30 pytest cases. PERF01 is an executable experiment, not
included in the 561 pytest count. TC04/TC06 supply more than two negative tests;
TC05/TC09 supply the mandatory exception failure path.

## Traceability
| AC / constraint | Cases | Executable file | Commit / evidence |
|---|---|---|---|
| AC1 | TC01,TC04,TC08 | T | red 6e96e30; patch178cd3a; green.txt,coverage.json |
| AC2 | TC02,TC08 | T | red6e96e30; patch178cd3a; red.txt -> green.txt |
| AC3 | TC03,TC07,TC09,TC12,TC13 | T | patch178cd3a; green.txt |
| AC4 | TC04,TC05,TC09 | T | patch178cd3a; mutation.patch,mutation.txt,mutation.json |
| AC5 | TC01,TC06,TC07,TC13 +531 old cases | T and existing backend/tests | baseline5206769; patch178cd3a; baseline.txt,green.txt |
| NFC1/NFC3 | TC05,TC07,TC08,TC10,TC11 | T | patch178cd3a; repeat-1..5.txt,repeat.json |
| NFC2 | PERF01 | homework/VT-045/experiments.py +harness.py | patch178cd3a; load.json,load-server.txt |

## Risk coverage and limits
All five AC have directly asserted positive/negative outcomes. The prescribed
mutation checks AC4's oracle, not all possible bugs. Line/branch percentages
identify executed code only. No claim about authentication, production policy
approval, atomic replacement on a network filesystem, prolonged load, full
review/export, real OCR/VLM latency, or per-run policy-hash integration in the
existing extraction metadata (R12). Those remain future work.
