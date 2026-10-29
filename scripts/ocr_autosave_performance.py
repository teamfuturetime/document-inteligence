"""Executable VT-043 HTTP load experiment; temporary DB, real auth and CSRF.

Run: python scripts/ocr_autosave_performance.py --concurrency 80 --transport tcp
Requires the project's backend + development dependencies. No production URL or
credentials are accepted: the harness only creates disposable local test data.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from contextlib import AsyncExitStack, contextmanager
from datetime import datetime, timezone
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import socket
import sqlite3
import sys
import tempfile
from threading import Event, Thread
from time import perf_counter

import httpx

# Direct execution puts scripts/ on sys.path; module execution puts the root on it.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ocr_autosave_support import (  # noqa: E402
    RAW_OCR, Document, isolated_http_environment, login_owner, register_owner,
)


@contextmanager
def tcp_server(application):
    import uvicorn

    ready = Event()

    class ReadyServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            if self.started:
                ready.set()

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    address = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server = ReadyServer(uvicorn.Config(application, log_level="error", access_log=False))
    thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        if not ready.wait(timeout=15):
            raise RuntimeError("local uvicorn did not become ready within 15 seconds")
        yield address
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        listener.close()
        if thread.is_alive():
            raise RuntimeError("local uvicorn did not stop within 15 seconds")


def percentile(samples: list[float], percent: float) -> float:
    """Nearest-rank percentile, preserving the original observations."""
    return sorted(samples)[max(0, math.ceil(percent * len(samples)) - 1)]


def classify(status: int | None, contention: bool) -> str:
    if status == 200:
        return "success"
    if status == 409 and contention:
        return "expected_conflict"
    if status in {400, 422}:
        return "validation_error"
    if status is None:
        return "transport_error"
    if status >= 500:
        return "server_error"
    return "unexpected_status"


async def measure_scenario(environment, clients, name: str, contention: bool) -> dict:
    count = len(clients)
    owner = await clients[0].get("/api/v1/auth/me")
    assert owner.status_code == 200
    document_ids = environment.seed_documents(owner.json()["user"]["id"], 1 if contention else count)
    gate = asyncio.Event()

    async def request(index):
        document_id = document_ids[0] if contention else document_ids[index]
        text = f"{name} Vietnamese OCR draft {index}: Nguyễn Văn A"
        await gate.wait()
        started = perf_counter()
        status = None
        http_version = None
        outcome = None
        acknowledgement_valid = None
        error_type = None
        try:
            response = await asyncio.wait_for(clients[index].patch(
                f"/api/v1/documents/{document_id}/ocr-correction",
                json={"text": text, "expected_revision": 0},
            ), timeout=30)
            status = response.status_code
            http_version = response.http_version
            if status == 200:
                body = response.json()
                acknowledgement_valid = (
                    isinstance(body, dict) and body.get("ocr_revision") == 1
                    and body.get("ocr_text_cleaned") == text
                )
                if not acknowledgement_valid:
                    raise ValueError("Invalid autosave acknowledgement")
            outcome = classify(status, contention)
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            # Record type only; never serialize request headers/cookies/credentials.
            error_type = type(exc).__name__
            outcome = "transport_error"
        except Exception as exc:
            # A malformed HTTP 200 is an error, rather than an acknowledged save.
            # Keep all other samples and the final DB check even if one worker
            # encounters an unexpected client/decoder failure. Do not catch
            # cancellation, KeyboardInterrupt or other BaseException subclasses.
            error_type = type(exc).__name__
            outcome = "unexpected_error"
            if status == 200:
                acknowledgement_valid = False
        elapsed_ms = (perf_counter() - started) * 1000
        return {
            "index": index, "document_id": document_id, "status": status,
            "http_version": http_version,
            "outcome": outcome, "latency_ms": elapsed_ms,
            "acknowledgement_valid": acknowledgement_valid, "error_type": error_type,
        }

    tasks = [asyncio.create_task(request(index)) for index in range(count)]
    started = perf_counter()
    gate.set()
    rows = await asyncio.wait_for(asyncio.gather(*tasks), timeout=45)
    elapsed = perf_counter() - started
    outcomes = Counter(row["outcome"] for row in rows)
    successful = [row for row in rows if row["outcome"] == "success"]
    final_state = []
    with environment.sessions() as db:
        for document_id in document_ids:
            document = db.get(Document, document_id)
            winners = [row for row in successful if row["document_id"] == document_id]
            expected_text = (
                f"{name} Vietnamese OCR draft {winners[0]['index']}: Nguyễn Văn A"
                if len(winners) == 1 else None
            )
            final_state.append({
                "document_id": document_id, "revision": document.ocr_revision,
                "status": document.status, "raw_unchanged": document.ocr_text == RAW_OCR,
                "exactly_one_success": len(winners) == 1,
                "corrected_matches_success": expected_text is not None and document.ocr_text_corrected == expected_text,
            })
    state_valid = all(
        row["revision"] == 1 and row["status"] == "reviewed" and row["raw_unchanged"]
        and row["exactly_one_success"] and row["corrected_matches_success"]
        for row in final_state
    ) and all(row["acknowledgement_valid"] for row in successful)
    failures = count - outcomes["success"] - outcomes["expected_conflict"]
    expected_distribution = outcomes["success"] == (1 if contention else count) and (
        outcomes["expected_conflict"] == (count - 1 if contention else 0)
    )
    latencies = [row["latency_ms"] for row in rows]
    p95 = percentile(latencies, 0.95)
    return {
        "scenario": name, "concurrent_operations": count, "total_requests": count,
        "successful_requests": outcomes["success"], "failed_requests": failures,
        "expected_conflicts": outcomes["expected_conflict"],
        "http_status_distribution": dict(Counter(str(row["status"]) for row in rows)),
        "outcome_distribution": dict(outcomes),
        "p50_ms": percentile(latencies, 0.50), "p95_ms": p95,
        "p99_ms": percentile(latencies, 0.99), "min_ms": min(latencies), "max_ms": max(latencies),
        "total_elapsed_seconds": elapsed, "throughput_requests_per_second": count / elapsed,
        "database_final_state": final_state, "database_invariant_passed": state_valid,
        "correctness_passed": failures == 0 and state_valid and expected_distribution,
        "p95_target_ms": 2500, "p95_target_passed": p95 <= 2500,
        "requests": rows,
    }


async def run(environment, concurrency: int, address: str | None) -> list[dict]:
    async with AsyncExitStack() as stack:
        clients = []
        for _ in range(concurrency):
            # Preparation performs sequential logins. Do not reuse their idle
            # sockets at the server/client keepalive expiration boundary during
            # the measured burst. Each timed request includes a fresh TCP
            # connection, with no retry hiding transport failures.
            client = (httpx.AsyncClient(
                base_url=address, timeout=30, trust_env=False,
                limits=httpx.Limits(max_keepalive_connections=0),
            )
                      if address else environment.client())
            clients.append(await stack.enter_async_context(client))
        await register_owner(clients[0])
        # Real distinct HTTP auth sessions; preparation is outside timed requests.
        for client in clients[1:]:
            await login_owner(client)
        assert len({tuple(client.cookies.items()) for client in clients}) == concurrency
        return [
            await measure_scenario(environment, clients, "P-01-independent", False),
            await measure_scenario(environment, clients, "P-02-contention", True),
        ]


def summary(result: dict) -> str:
    env = result["environment"]
    lines = [
        "# VT-043: HTTP performance experiment", "",
        f"Run (UTC): {result['started_at_utc']}",
        f"OS: {env['os']}; Python: {env['python']}; SQLite: {env['sqlite_version']} (file DB, WAL).",
        f"Transport: {env['transport']}; concurrency: {env['concurrency']} released together by asyncio.Event.",
        "Every client obtains a distinct real login session; CSRF, ownership and endpoint validation remain enabled.", "",
        "| Scenario | Requests | 200 | Expected 409 | Failures | p50 ms | p95 ms | p99 ms | Correctness | p95 <= 2500 ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result["scenarios"]:
        lines.append(
            f"| {row['scenario']} | {row['total_requests']} | {row['successful_requests']} | "
            f"{row['expected_conflicts']} | {row['failed_requests']} | {row['p50_ms']:.2f} | "
            f"{row['p95_ms']:.2f} | {row['p99_ms']:.2f} | "
            f"{'PASS' if row['correctness_passed'] else 'FAIL'} | {'PASS' if row['p95_target_passed'] else 'FAIL'} |"
        )
    lines.extend([
        "", "Latency: perf_counter immediately before PATCH until response body is received; includes client connection setup, server queueing, auth/CSRF, SQL and serialization. Setup, registration/login and seeding are excluded.",
        "Percentiles use nearest rank: sorted samples[ceil(p*n)-1]. All raw samples, status/error classes, throughput, min/max, elapsed time and persisted-state assertions are in performance_results.json.",
        "", "Limits: one local run, disposable SQLite WAL database, single local application process, default AnyIO worker limit (normally 40), SQLAlchemy pool_size=20/max_overflow=80. 80 simultaneous client operations does not imply 80 SQL writers; SQLite serializes writes. PostgreSQL, remote network, production hardware, OCR processing and sustained-load behavior are NOT VERIFIED.",
        "The 409 responses in P-02 are expected concurrency protection; they are excluded from failed_requests and included in latency percentiles.",
    ])
    if env["transport"] == "asgi-in-process":
        lines.append("ASGITransport invokes the full HTTP application stack in process and excludes TCP/socket/server overhead; this result is not a TCP benchmark.")
    else:
        lines.append("Connection policy: HTTPX max_keepalive_connections=0; every timed request establishes a new TCP connection. No retries. Per-response HTTP version is recorded in the JSON samples.")
    if not all(row["p95_target_passed"] for row in result["scenarios"]):
        lines.append("p95 FAILED: investigate SQLite serialized writes and application worker/pool queueing; preserve this run before any controlled optimization and rerun. Do not replace this evidence with edited measurements.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concurrency", type=int, default=80)
    parser.add_argument("--transport", choices=["tcp", "asgi"], default="tcp")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "evidence" / "bt3-vt043")
    args = parser.parse_args()
    if not 2 <= args.concurrency <= 200:
        parser.error("concurrency must be between 2 and 200")
    started_at = datetime.now(timezone.utc).isoformat()
    started = perf_counter()
    with tempfile.TemporaryDirectory(prefix="vt043-http-") as temporary:
        with isolated_http_environment(Path(temporary)) as environment:
            if args.transport == "tcp":
                with tcp_server(environment.application) as address:
                    scenarios = asyncio.run(run(environment, args.concurrency, address))
            else:
                scenarios = asyncio.run(run(environment, args.concurrency, None))
    packages = {}
    for package in ["fastapi", "sqlalchemy", "httpx", "uvicorn", "anyio"]:
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = "not installed"
    result = {
        "execution_status": "EXECUTED", "started_at_utc": started_at,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "whole_experiment_seconds": perf_counter() - started,
        "environment": {
            "os": platform.platform(), "python": platform.python_version(),
            "sqlite_version": sqlite3.sqlite_version, "database": "temporary file SQLite WAL",
            "transport": "loopback TCP / uvicorn" if args.transport == "tcp" else "asgi-in-process",
            "concurrency": args.concurrency, "packages": packages,
            "sqlalchemy_pool_size": 20, "sqlalchemy_max_overflow": 80,
            "busy_timeout_seconds": 20, "request_timeout_seconds": 30,
            "max_keepalive_connections": 0 if args.transport == "tcp" else None,
            "retries": 0,
        },
        "latency_method": "perf_counter around HTTP PATCH to completed response body; milliseconds; nearest-rank percentiles",
        "scenarios": scenarios,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "performance_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "performance_summary.md").write_text(summary(result), encoding="utf-8")
    print(summary(result))
    return 0 if all(row["correctness_passed"] and row["p95_target_passed"] for row in scenarios) else 1


if __name__ == "__main__":
    raise SystemExit(main())
