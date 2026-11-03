"""VT-042: 150 simultaneous TCP requests, real SQLite/files, explicit OCR doubles."""

import argparse
import asyncio
import io
import json
import math
import platform
import socket
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx2
import uvicorn
from docintel.api.app import create_app
from docintel.config import Settings
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PATH = (
    "/api/v1/documents?document_type=hoa_don&data_origin=synthetic&filename=sample.png"
)


async def measure(scenario):
    with tempfile.TemporaryDirectory(prefix="vt042-load-") as folder:
        settings = Settings(
            _env_file=None, provider_mode="tesseract", runtime_dir=Path(folder)
        )
        with (
            patch(
                "docintel.services.documents.DocumentService.ensure_ready",
                lambda self: {},
            ),
            patch(
                "docintel.services.documents.prepare_image",
                lambda data, config: SimpleNamespace(png=data, width=12, height=12),
            ),
        ):
            app = create_app(settings, start_worker=False)
            listener = socket.socket()
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
            server = uvicorn.Server(
                uvicorn.Config(app, log_level="error", access_log=False)
            )
            thread = threading.Thread(
                target=server.run, kwargs={"sockets": [listener]}, daemon=True
            )
            thread.start()
            try:
                deadline = time.perf_counter() + 10
                while not server.started:
                    if time.perf_counter() > deadline:
                        raise RuntimeError("Load server did not start")
                    await asyncio.sleep(0.01)
                buffer = io.BytesIO()
                Image.new("RGB", (12, 12), "white").save(buffer, format="PNG")
                data = buffer.getvalue()
                gate = asyncio.Event()
                active = peak = 0
                async with httpx2.AsyncClient(
                    base_url=f"http://127.0.0.1:{port}",
                    timeout=30,
                    trust_env=False,
                    limits=httpx2.Limits(
                        max_connections=150, max_keepalive_connections=150
                    ),
                ) as client:
                    document_id = None
                    if scenario != "unique_upload":
                        seed = await client.post(
                            PATH, headers={"Idempotency-Key": "REPLAY"}, content=data
                        )
                        assert seed.status_code == 202
                        document_id = seed.json()["document_id"]

                    async def one(number):
                        nonlocal active, peak
                        await gate.wait()
                        active += 1
                        peak = max(peak, active)
                        started = time.perf_counter()
                        try:
                            if scenario == "status_poll":
                                response = await client.get(
                                    "/api/v1/documents/" + document_id
                                )
                            else:
                                key = (
                                    "REPLAY"
                                    if scenario == "same_key_retry"
                                    else f"K{number:03}"
                                )
                                response = await client.post(
                                    PATH, headers={"Idempotency-Key": key}, content=data
                                )
                            body = response.json()
                            return {
                                "request": number,
                                "status": response.status_code,
                                "elapsed_ms": (time.perf_counter() - started) * 1000,
                                "document_id": body.get("document_id"),
                                "run_id": body.get("run", {}).get("run_id"),
                                "run_status": body.get("run", {}).get("status"),
                            }
                        except (httpx2.HTTPError, ValueError) as exc:
                            return {
                                "request": number,
                                "status": "ERROR",
                                "elapsed_ms": (time.perf_counter() - started) * 1000,
                                "error_type": type(exc).__name__,
                            }
                        finally:
                            active -= 1

                    tasks = [asyncio.create_task(one(i)) for i in range(150)]
                    await asyncio.sleep(0)
                    started = time.perf_counter()
                    gate.set()
                    rows = await asyncio.gather(*tasks)
                    elapsed = time.perf_counter() - started
                with app.state.documents.repository.transaction() as connection:
                    counts = {
                        name: connection.execute(
                            "SELECT count(*) FROM " + name
                        ).fetchone()[0]
                        for name in ("documents", "runs", "events")
                    }
                ordered = sorted(row["elapsed_ms"] for row in rows)
                statuses = dict(Counter(str(row["status"]) for row in rows))
                expected = (
                    {"202": 5, "429": 145}
                    if scenario == "unique_upload"
                    else ({"200": 150} if scenario == "status_poll" else {"202": 150})
                )
                count = 5 if scenario == "unique_upload" else 1
                correct = statuses == expected and all(
                    value == count for value in counts.values()
                )
                if scenario != "unique_upload":
                    correct = (
                        correct and len({row.get("document_id") for row in rows}) == 1
                    )
                    correct = correct and len({row.get("run_id") for row in rows}) == 1
                return {
                    "scenario": scenario,
                    "concurrency": 150,
                    "peak_inflight_client": peak,
                    "requests": 150,
                    "payload_bytes": len(data),
                    "queue_capacity": settings.max_pending_runs,
                    "worker_started": False,
                    "transport": "TCP loopback HTTP/1.1 Uvicorn",
                    "statuses": statuses,
                    "p50_ms": ordered[math.ceil(0.50 * len(rows)) - 1],
                    "p95_ms": ordered[math.ceil(0.95 * len(rows)) - 1],
                    "p99_ms": ordered[math.ceil(0.99 * len(rows)) - 1],
                    "wall_seconds": elapsed,
                    "requests_per_second": 150 / elapsed,
                    "db_counts": counts,
                    "correctness_passed": correct,
                    "response_p95_target_ms": 4000,
                    "response_p95_passed": ordered[142] <= 4000,
                    "rows": rows,
                }
            finally:
                server.should_exit = True
                thread.join(timeout=10)
                if thread.is_alive():
                    raise RuntimeError("Load server did not stop")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "runtime/vt042/performance.json"
    )
    args = parser.parse_args()
    results = []
    for scenario in ("unique_upload", "same_key_retry", "status_poll"):
        result = await measure(scenario)
        results.append(result)
        print(
            json.dumps(
                {key: value for key, value in result.items() if key != "rows"}, indent=2
            ),
            flush=True,
        )
    report = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "percentile": "nearest rank ceil(p*N); all statuses included",
        "runs": results,
        "scope": "Control-plane response latency, actual TCP/SQLite/files; readiness/decode doubles; no OCR completion measured",
        "limitations": [
            "One local Windows machine",
            "150 clients, not 150 workers",
            "Capacity 5 rejects 145 new uploads in the unique-key workload",
            "One run per scenario; no production/WAN or 150 OCR completion claim",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    assert all(result["correctness_passed"] for result in results)


if __name__ == "__main__":
    asyncio.run(main())
