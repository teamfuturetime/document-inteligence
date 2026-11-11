"""Deterministic local HTTP/ASGI load, not a network/provider/OCR benchmark."""

import argparse
import asyncio
from collections import Counter
import json
import logging
import math
import platform
from time import perf_counter

import httpx2

from document_backend.main import create_app

WORKERS = 40
LIMIT = 32 * 1024


class ProbeSender:
    def __init__(self, outcome):
        self.outcome = outcome
        self.events = Counter()
        self.cancelled = 0

    async def send(self, event):
        self.events[event.invoice_number] += 1
        if self.outcome == "error":
            raise OSError("synthetic failure")
        if self.outcome == "hang":
            try:
                await asyncio.Event().wait()
            finally:
                self.cancelled += 1
        else:
            await asyncio.sleep(0.005)  # Controlled nonzero delivery time.


async def scenario(name, size, outcome, rounds):
    app = create_app()
    sender = ProbeSender(outcome)
    app.state.review_notifier = sender
    durations, errors = [], []
    active = peak = 0
    ready = asyncio.Event()
    expected_status = 413 if size > LIMIT else 200

    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),
                                  base_url="http://vt046.local", trust_env=False) as client:
        async def worker(index):
            nonlocal active, peak
            await ready.wait()
            for iteration in range(rounds):
                number = f"VT046-{index:02}-{iteration:03}"
                raw = json.dumps({"schema_version": "1.0.0", "values": {
                    "invoice_number": number, "invoice_date": "2024-02-29",
                    "seller_name": "Cửa hàng Mây Việt", "total_amount": "125.000",
                    "currency": "vnđ"}}, ensure_ascii=False).encode()
                if size:
                    raw += b" " * (size - len(raw))

                async def chunks():
                    for offset in range(0, len(raw), 8192):
                        await asyncio.sleep(0)  # Cooperative receive, including chunked oversize.
                        yield raw[offset:offset + 8192]

                active += 1
                peak = max(peak, active)
                started = perf_counter()
                try:
                    response = await client.post("/api/v1/validate", content=chunks(),
                                                 headers={"content-type": "application/json"})
                    durations.append(perf_counter() - started)
                    assert response.status_code == expected_status
                    result = response.json()
                    if expected_status == 200:
                        assert result == {"schema_version": "1.0.0", "valid": True, "errors": [],
                            "normalized_values": {"invoice_number": number,
                                "invoice_date": "2024-02-29", "seller_name": "Cửa hàng Mây Việt",
                                "total_amount": 125000, "currency": "VND"}}
                    else:
                        assert result["error"]["code"] == "invalid_request"
                except Exception as exc:
                    errors.append(f"{number}: {type(exc).__name__}: {exc}")
                finally:
                    active -= 1

        tasks = [asyncio.create_task(worker(i)) for i in range(WORKERS)]
        started = perf_counter()
        ready.set()
        await asyncio.gather(*tasks)
        elapsed = perf_counter() - started
    expected_events = WORKERS * rounds if expected_status == 200 else 0
    assert sum(sender.events.values()) == expected_events
    assert all(count == 1 for count in sender.events.values())
    assert sender.cancelled == (expected_events if outcome == "hang" else 0)
    ordered = sorted(durations)
    p95 = ordered[math.ceil(0.95 * len(ordered)) - 1] if ordered else None
    passed = not errors and len(durations) == WORKERS * rounds and p95 <= 1.5 and peak == WORKERS
    return {"scenario": name, "workers": WORKERS, "rounds_per_worker": rounds,
            "requests": len(durations), "peak_in_flight": peak, "expected_status": expected_status,
            "body_bytes": size or "~225-300 UTF-8 bytes", "send_outcome": outcome,
            "p50_ms": round(ordered[len(ordered)//2] * 1000, 3),
            "p95_ms": round(p95 * 1000, 3), "max_ms": round(max(ordered) * 1000, 3),
            "elapsed_s": round(elapsed, 3), "requests_per_second": round(len(ordered)/elapsed, 2),
            "event_attempts": sum(sender.events.values()), "cancelled_sends": sender.cancelled,
            "errors": errors, "target_p95_ms": 1500, "passed": passed}


async def main(rounds):
    logging.disable(logging.CRITICAL)
    rows = []
    for name, size, outcome in [("small_success", 0, "ok"),
                                ("at_limit_success", LIMIT, "ok"),
                                ("oversized_2MiB", 2 * 1024 * 1024, "ok"),
                                ("provider_exception", 0, "error"),
                                ("provider_stall", 0, "hang")]:
        rows.append(await scenario(name, size, outcome, rounds))
    print(json.dumps({"python": platform.python_version(), "platform": platform.platform(),
                      "transport": "httpx2.ASGITransport; one event loop; no sockets",
                      "quantile": "nearest-rank ceil(0.95*N)", "results": rows},
                     ensure_ascii=False, indent=2))
    return all(row["passed"] for row in rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=10)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    raise SystemExit(0 if asyncio.run(main(args.rounds)) else 1)
