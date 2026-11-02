# AI implementation plan v1 (before tests and production patch)

Baseline: `52067697c1e4505eb36042e5fbe525ed984d2637`.
Agent: Codex, session 2026-11-02 (Asia/Saigon). Student: 23001948.

User prompt: “hãy thực hiện yêu cầu. lưu ý kỹ đầu ra”, referring to hw3.txt VT-045.
The preceding request supplied Lecture 06 and Lecture 07 as reading material.

Proposed vertical slice: configurable maximum accepted invoice total in JSON.
The existing requirements do not specify an accounting ceiling. This is an
additive, explicitly scoped homework policy, not an inferred stakeholder rule.
Default must preserve all existing canonical amounts.

Initial implementation choices to audit against the repository:
1. Put the configured ceiling directly into the Pydantic `Amount` bound.
2. Expose a production `/validate` API to run E2E and performance tests.
3. Load JSON on each validation call; propagate a sanitized configuration error.
4. Assert complete business outcomes, not merely HTTP success codes.

Expected files: backend/app/schemas/invoice.py, backend/app/services/validation.py,
backend/app/main.py, a new policy JSON/loader, contract tests, a homework harness,
experiment scripts and the PDF report. Review these choices before coding.

Assumptions to verify: schema ceiling is a business threshold; a validation API
already exists; a fake-provider/load harness can establish full product latency.
Stop if these claims are unsupported. Do not download a model or call external AI.
