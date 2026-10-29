# Performance experiment review and retained failure

All runs below used 80 simultaneous client operations, a disposable SQLite WAL database, real independent authentication sessions, CSRF and the full FastAPI HTTP endpoint over loopback TCP. Data were seeded before timing and verified from a new SQLAlchemy Session after all requests completed. No requests were retried.

| Run (UTC, 2026-10-29) | P-01 successes / failures | P-01 p95 ms | P-02 success / expected conflict | P-02 p95 ms | Evidence prefix |
|---|---:|---:|---:|---:|---|
| 13:55:07 | 80 / 0 | 2152.16 | 1 / 79 | 1191.68 | `performance_initial_*` |
| 14:00:29 | 79 / 1 | 1924.73 | 1 / 79 | 1642.01 | `performance_transport_failure_*` |
| 14:02:19 | 80 / 0 | 1834.90 | 1 / 79 | 1306.35 | `performance_results.json`, `performance_summary.md`, `performance_run.log` |

The middle run is FAILED for P-01 despite meeting the p95 target. Client operation 12 recorded `ReadError`, no HTTP status, and 174.23 ms latency. Its document remained at revision 0 with its original OCR; the other 79 documents saved successfully. P-02 had exactly one persisted winner and 79 expected HTTP 409 responses. Captured server output contains only application start/stop INFO records, with no ERROR or CRITICAL records and no database exception traceback. Absence of a server traceback does not establish the exact transport failure cause.

Diagnosis: the observed error is a transport failure rather than an acknowledged save or a revision conflict. An idle connection expiration race is an **inference**, not a proven root cause: sequential preparation logins leave connections of different ages, and local inspection confirmed HTTPX's default keepalive expiry and uvicorn's keepalive timeout are both five seconds. The retained evidence records the exception type without its message or socket diagnostics, so the exact connection close/reset cause cannot be recovered from this run.

Controlled harness change: TCP clients now use `httpx.Limits(max_keepalive_connections=0)`. Every timed request establishes a new TCP connection, so preparation sockets cannot be reused at an idle timeout boundary. This changes the benchmark's connection policy and includes connection establishment in every latency sample. No sleeps, automatic retries or changes to server/database concurrency protection were added. The final run passed with this explicit policy; it does not prove the inferred cause of the earlier transient error. Initial, failed and final JSON, summaries and stdout are all retained.

Harness error reporting was also tested with real application writes followed by a corrupted client response. Four tests deliberately inject invalid JSON, an incorrect JSON type, a mismatched revision/text acknowledgement, and an unexpected client exception. All four failed before the harness fix (`performance_harness_fail_before.log`), then passed (`performance_harness_pass_after.log`). A malformed HTTP 200 now counts as `unexpected_error`, does not count as an acknowledged winner, preserves the remaining samples and final-state report, and stores only an exception class name. A marker in the synthetic response/exception message is asserted absent from serialized results.

Remaining limits: local single-process uvicorn, SQLite serialized writers, one run per listed configuration, no PostgreSQL, remote-network or sustained-load verification. The final run's p95 PASS is limited to its documented connection policy and environment. The initial and final p95 values must not be interpreted as a statistically established optimization effect.
