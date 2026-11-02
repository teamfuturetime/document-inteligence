# VT-045 specification and reviewed plan

## Problem statement
Changing an operational acceptance ceiling for invoice totals currently has no
external policy mechanism. Add one JSON source of truth at the validation boundary
so an operator can change the ceiling without editing Python or frontend code.
This is a new homework policy layered over R05; it does not change sales_invoice
1.0.0, declare an accounting limit, or implement review/export confirmation.

## Acceptance criteria
- AC1: `backend/config/invoice-policy.json` supplies a strict, versioned integer
  `max_total_amount` in [0, 9007199254740991]. Default equals the schema ceiling;
  all formerly valid values remain supported with the shipped default.
- AC2: Changing only that JSON between calls changes acceptance in the same
  process: 125000 passes at 200000, fails at 100000. No restart or source edit.
- AC3: At/below the policy ceiling the amount remains unchanged. Above it,
  `valid=false`, `total_amount=null`, and exactly one field error with code
  `business.amount_exceeds_policy`; other valid fields and input remain intact.
- AC4: Missing, unreadable, malformed, duplicate-key or invalid configuration
  raises `InvoicePolicyError`. No fallback data or fabricated successful result.
  The local HTTP harness maps that failure to a sanitized 503 error-only response.
- AC5: Existing schema/normalization errors, five required keys, VND-only rule,
  no inferred user confirmation and `ValidationResult` JSON envelope stay intact.

## Non-functional constraints
- NFC1: no extra production dependency, network, database or model required;
  immutable policy snapshot per call, no shared cache; only synthetic data.
- NFC2: verify 100 concurrent tasks against p95 <=3.0 seconds for the local
  validation harness; include errors in the denominator and assert outcomes.
  This does not establish OCR/VLM or production capacity.
- NFC3: invalid config fails closed without exposing file paths or contents.
  Deploy config with atomic file replacement; no guarantee across multiple files.

## Contract and invariants explained before implementation
Consumer: pipeline or HTTP harness. Provider: normalization + validation service.
The five-field canonical schema has an immutable safe-integer ceiling. Policy can
only narrow acceptance. For valid canonical amount a and loaded ceiling M, the
policy accepts iff a<=M. Existing input errors always prevent acceptance.
`valid` agrees with completeness and absence of errors. Invalid config is a
system failure, never an ordinary successful invoice with defaults. Do not assert
only HTTP status: assert values, error code/field, nulling, unchanged other fields,
and absence of a successful payload on system failure.

## Review of v1 against real evidence (before production patch)
1. **Reject modifying `Amount`.** docs/requirements.md, table `total_amount` and
   paragraph immediately below it: 9007199254740991 is a JSON/JavaScript safety
   boundary, explicitly not an accounting/business limit. schemas/invoice.py
   reuses `Amount` for both canonical models. Keep schema unchanged; apply a
   separate stricter policy in services/validation.py after canonical checks.
2. **Reject adding a production route.** app/main.py has only GET /health;
   docs/requirements.md R05 and docs/architecture.md say the validation API and
   frontend integration are not implemented. Use the assignment's executable
   harness option instead of expanding production scope or claiming browser E2E.
3. **Reject claiming full-product latency from fake data.** README.md and
   docs/architecture.md distinguish fake extraction from actual OCR/VLM. Measure
   real loopback HTTP validation with synthetic records and state the limit.

## Corrected implementation plan
1. Save baseline and v1/review. Write business-outcome contract tests first.
2. Execute a reload test against baseline service; save its assertion failure.
3. Add strict policy loader + JSON; optional keyword `policy_path` seam for tests.
   Keep the old positional validation API and envelope. Add policy rejection to
   existing error handling; default file resolved relative to module, not CWD.
4. Add homework-only HTTP app and contract tests for 200 business rejection / 503
   system failure. Run complete backend regression and collect branch coverage.
5. Create swallowed-exception mutation in an isolated temporary source tree;
   run an existing failure-path contract test, retain patch/log/hash, discard tree.
6. Check shared state/order/concurrency and time independence; repeat deterministically.
   Run loopback HTTP with 100 released-together clients, outcome oracle, p95.
7. Commit scoped changes/evidence, publish homework branch without merge, produce
   <=8-page main PDF plus clearly separated appendices; render/inspect every page.

Final production files: backend/config/invoice-policy.json,
backend/app/services/invoice_policy.py, backend/app/services/validation.py.
Other changes: backend/tests/test_invoice_policy.py and homework/VT-045/ only,
plus output/pdf/BT3_23001948_VT-045.pdf. Preserve the user's docs/testing.md edit.

AI performed this repository review. It is not represented as a completed human
peer review. Student must inspect the final diff and reflection before submission.
