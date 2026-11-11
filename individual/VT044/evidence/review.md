# Agent diff review (not human sign-off)

Reviewed final lifecycle patch against the RED scaffold before acceptance:

- Ownership is in the UPDATE predicate; a foreign ID cannot even acquire the
  write lock. Reads, list, content and extraction independently scope access.
- The tombstone row and real Document row are locked before checking processing
  and expiry. A UTC clock is injectable. Expiry is never extended by restore.
- Only the sidecar boolean is changed. No delete, unlink, extraction edit or
  status rewrite is introduced (the status UPDATE is intentionally a no-op).
- Commit failures roll back. The failure test flushes SQL before raising and
  reads from a fresh session; an HTTP 503 alone would not prove rollback.
- Idempotent transitions commit successfully; checking the persisted state and
  subsequent reads avoids trusting a response that merely echoes the target.
- The mutation experiment proves the last point with a failing assertion.
- `git diff --check` passed. No production module was edited.

Residual concerns: returning FileResponse has a file-open time gap; external
retention can remove bytes after access checks. Reads use no snapshot spanning
the entire streamed response. Original production endpoints bypass the harness.
No claim of end-to-end production isolation is justified.

HTTP load was run twice: the second run adds tracebacks after the first run
reported errors. It shows client httpx/httpcore/anyio ReadError and AttributeError
in socket metadata (`NoneType.getpeername`). These traces do not establish the
root cause or server capacity. Neither incomplete run is a passing SLA result.

## Completion review

The lifecycle implementation is unchanged. Six new test instances cover
same-document owner/foreign contention, missing extraction/file and expired
active reads. All 34 contracts and 133 total tests pass. Coverage is now 93/93
lines and 18/18 branches of this small harness, not the full application.

The two preplanned stdlib HTTP runs still exhibit initial connection resets:
199/200 and 195/200 tasks succeed. They fail overall despite p95 below 5s.
This contradicts any explanation blaming ONLY the async HTTP library; the
network-boundary root cause remains unproven. No retries or concurrency
reduction were used. The ASGI-only mode runs all 200 tasks and validates all
1,200 responses and final extraction/file state, with zero errors and p95
1.136s. It omits sockets and must not be described as production/network SLA.

The new load command returns success only if response correctness, complete
request counts, all final state checks and p95 <=5s are satisfied. Its raw JSON
retains per-request outcomes. The original load results remain unchanged.

The student actually rejected the shared-key assumption during this completion
review (`student-review.md`); do not backdate it or infer full code sign-off.
