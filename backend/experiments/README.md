# VT-046: review notification vertical slice

Branch: `feat/vt046-validation-notification` (no merge).
Baseline: `c884a0b6c53eab169eb7ef696ae297ec89464383`.
Tests-first commit: `f8a1c0f`; implementation: `21cb780`.

From repository root, Python >=3.11:

```sh
uv sync --locked
uv pip install --python .venv/bin/python pytest-cov==7.1.0 coverage==7.17.2
.venv/bin/python -m pytest backend/tests/test_notifications.py backend/tests/test_review_validation.py backend/tests/test_api.py -q
.venv/bin/python -m pytest backend/tests -q --cov=document_backend.api.validate --cov=document_backend.services.notifications --cov=document_backend.services.validation --cov=document_backend.main --cov-branch --cov-report=term-missing
.venv/bin/python backend/experiments/vt046_mutation.py
.venv/bin/python backend/experiments/vt046_flake.py
.venv/bin/python backend/experiments/vt046_load.py --rounds 10
```

`POST /api/v1/validate` computes the existing validation result, then attempts one
`review.validated` event only if valid. The default adapter writes the event name
to an application log. Set `app.state.review_notifier` to an object with async
`send(event)` for another adapter (see tests). No recipient/provider is configured.
This is an executable notification seam and logging sink, not production email.

Contracts: response schema unchanged; invalid fields still return 200/valid=false;
bad schema returns 422. Notification errors/cooperative 50ms timeout preserve the
computed response. Event is frozen and includes only normalized invoice number
and event name; logs omit invoice values and raw exception details. Async senders
must not block the event loop and must honor cancellation. Caller cancellation
propagates. Body bytes are capped at 32768 before JSON parsing (413 invalid_request),
with a 1-second receive deadline (504 processing_timeout).

Equivalence partitions: valid normalized values; schema-valid business errors;
malformed/type/extra/overlong wire data; <=32KiB vs >32KiB actual bytes;
provider success/exception/stall. Boundary representatives: 32767/32768/32769
bytes and 1000/1001-character fields. Data are synthetic, deterministic and local.

Historical red run on tests-only commit: 14 failed, 9 passed, before implementation.
Patch: 53 focused passed; backend 132 passed / 3 optional OCR tests skipped.
Mutation branch `test/vt046-response-mutation`, commit `dbef11a`, changes mapping
`normalized_values.seller_name <- invoice_number`; three exact-response assertions
fail. The submission branch excludes that commit. Mutation harness reproduces the
same change in a temporary package copy, proves the imported path, and requires
assertion failures with the mismatched values; exit 0 means mutant killed. It never
writes production source. Revisit its anchor if validation implementation changes.

Flake probe: 3 normal + 3 reversed runs in fresh subprocesses, each with 30s watchdog.
It checks time/cancellation and order/state risks; passing is not proof of no flakes.
There are no provider/network calls or random values in focused tests.

Load harness: 40 concurrent async workers x 10 sequential requests each per scenario,
5 scenarios (small, exact limit, oversized 2MiB, provider error, provider stall).
Each worker has distinct invoice numbers; the harness checks exact response values,
event count/isolation and cancellation, plus p95 <=1500ms and peak in-flight=40.
Latency uses perf_counter and nearest-rank ceil(0.95*N), measured from client.post to
completed in-process response. Bodies stream in 8KiB chunks; asyncio.sleep(0) models
cooperative receive. Successful fake sends wait 5ms; stalled sends await cancellation.
Oversized bodies are rejected before all chunks are consumed. Timing excludes body
construction and includes ASGI/client/parse/notification work. There is no warmup;
all 400 samples per scenario are included. JSON output includes runtime/platform.

Limitations: one process/event loop, no sockets/TLS/proxy, no real OCR/DB/provider,
no CPU/RSS profiling, sustained deployment saturation or durable delivery guarantee.
Application body cap supplements ingress caps; it cannot undo a huge ASGI server
chunk allocation. No client retry deduplication; best-effort delivery may be lost.
All report/PDF/raw evidence live outside source commits in local `output/`.
