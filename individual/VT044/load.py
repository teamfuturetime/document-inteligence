"""200 barrier-released tasks over actual loopback HTTP; synthetic documents."""
import asyncio
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import json
from http.client import HTTPConnection
import math
from pathlib import Path
import platform
import socket
import tempfile
import threading
import time
import traceback

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import uvicorn

from app.models import Base, Document, Extraction
from app.services.storage import LocalStorage
from individual.VT044.harness import Lifecycle, LifecycleService, create_app


N = 200


def percentile(values, fraction):
    return sorted(values)[math.ceil(len(values) * fraction) - 1]


async def exercise(port, ids, *, app=None):
    gate = asyncio.Event()
    request_seconds, task_seconds, errors, records, successes = [], [], [], [], []
    released_at = []
    limits = httpx.Limits(max_connections=N, max_keepalive_connections=N)
    transport = httpx.ASGITransport(app=app) if app is not None else None
    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", limits=limits,
                                 transport=transport, timeout=30) as client:
        async def task(index):
            headers = {"X-API-Key": f"demo-{index}"}
            path = f"/documents/{ids[index]}"
            await gate.wait()
            succeeded, completed = True, 0
            steps = [
                ("DELETE", path, 200), ("GET", path, 404),
                ("GET", f"/documents/{ids[(index + 1) % N]}", 404),
                ("POST", path + "/restore", 200), ("GET", path, 200),
                ("GET", path + "/content", 200),
            ]
            try:
                for step, (method, url, expected) in enumerate(steps):
                    before = time.perf_counter()
                    response = await client.request(method, url, headers=headers)
                    duration = time.perf_counter() - before
                    request_seconds.append(duration)
                    completed += 1
                    valid = response.status_code == expected
                    if valid and step in (0, 3):
                        valid = response.json() == {"id": ids[index], "deleted": step == 0}
                    elif valid and expected == 404:
                        valid = response.json() == {"detail": "Không tìm thấy tài liệu"}
                    elif valid and step == 4:
                        valid = response.json() == {"id": ids[index], "status": "confirmed"}
                    elif valid and step == 5:
                        valid = response.content == f"synthetic-{index}".encode()
                    records.append({"task": index, "step": step, "method": method,
                                    "status": response.status_code, "expected": expected,
                                    "seconds": duration, "valid": valid})
                    if not valid:
                        succeeded = False
                        errors.append({"task": index, "step": step, "problem": "status or payload mismatch"})
            except Exception as error:
                succeeded = False
                errors.append({"task": index, "exception": type(error).__name__, "traceback": traceback.format_exc()})
            finally:
                successes.append(succeeded and completed == 6)
                task_seconds.append(time.perf_counter() - released_at[0])

        pending = [asyncio.create_task(task(index)) for index in range(N)]
        await asyncio.sleep(0)  # All tasks reach the gate; no artificial timed sleep.
        started = time.perf_counter()
        released_at.append(started)
        gate.set()
        await asyncio.gather(*pending)
        elapsed = time.perf_counter() - started
    return {
        "transport": "ASGI in-process; no socket or network" if app is not None else "httpx async over loopback HTTP",
        "concurrent_tasks": N, "completed_tasks": len(task_seconds),
        "successful_tasks": sum(successes), "failed_tasks": len(successes) - sum(successes),
        "requests": len(request_seconds), "expected_requests": 6 * N,
        "error_count": len(errors), "errors": errors,
        "task_p50_seconds": percentile(task_seconds, .50),
        "task_p95_seconds": percentile(task_seconds, .95),
        "task_max_seconds": max(task_seconds),
        "request_p95_seconds": percentile(request_seconds, .95) if request_seconds else None,
        "elapsed_seconds": elapsed,
        "percentile_method": "nearest rank ceil(0.95*n); task clock starts at common barrier release",
        "task_latencies_seconds": task_seconds,
        "request_latencies_seconds": request_seconds,
        "request_records": records,
    }


def exercise_stdlib(port, ids, *, connection_mode="cold"):
    """Isolate client transport while retaining all 200 simultaneous tasks.

    Each worker owns its socket. No retries or reduction in measured concurrency.
    Cold mode includes connection setup in latency. Preconnected mode explicitly
    records setup separately; it does not measure cold-connection capacity.
    """
    if connection_mode not in ("cold", "preconnected"):
        raise ValueError("unknown connection mode")
    prepared, setup_records = {}, []
    released_at = []
    gate = threading.Barrier(N, action=lambda: released_at.append(time.perf_counter()), timeout=20)

    def task(index):
        path = f"/documents/{ids[index]}"
        headers = {"X-API-Key": f"demo-{index}"}
        steps = [
            ("DELETE", path, 200), ("GET", path, 404),
            ("GET", f"/documents/{ids[(index + 1) % N]}", 404),
            ("POST", path + "/restore", 200), ("GET", path, 200),
            ("GET", path + "/content", 200),
        ]
        records, errors = [], []
        connection = (prepared[index] if connection_mode == "preconnected"
                      else HTTPConnection("127.0.0.1", port, timeout=30))
        gate.wait()
        try:
            for step, (method, url, expected) in enumerate(steps):
                before = time.perf_counter()
                connection.request(method, url, headers=headers)
                response = connection.getresponse()
                payload = response.read()
                duration = time.perf_counter() - before
                valid = response.status == expected
                if valid and step in (0, 3):
                    valid = json.loads(payload) == {"id": ids[index], "deleted": step == 0}
                elif valid and expected == 404:
                    valid = json.loads(payload) == {"detail": "Không tìm thấy tài liệu"}
                elif valid and step == 4:
                    valid = json.loads(payload) == {"id": ids[index], "status": "confirmed"}
                elif valid and step == 5:
                    valid = payload == f"synthetic-{index}".encode()
                record = {"task": index, "step": step, "method": method,
                          "status": response.status, "expected": expected,
                          "seconds": duration, "valid": valid}
                records.append(record)
                if not valid:
                    errors.append({"task": index, "step": step, "problem": "status or payload mismatch"})
        except Exception as error:
            errors.append({"task": index, "exception": type(error).__name__,
                           "traceback": traceback.format_exc()})
        finally:
            connection.close()
        return {"task": index, "seconds": time.perf_counter() - released_at[0],
                "records": records, "errors": errors,
                "success": len(records) == 6 and not errors}

    with ExitStack() as cleanup:
        setup_seconds = 0.0
        if connection_mode == "preconnected":
            setup_started = time.perf_counter()
            for index, document_id in enumerate(ids):
                connection = HTTPConnection("127.0.0.1", port, timeout=30)
                cleanup.callback(connection.close)
                before = time.perf_counter()
                connection.request("GET", f"/documents/{document_id}",
                                   headers={"X-API-Key": f"demo-{index}"})
                response = connection.getresponse()
                payload = response.read()
                valid = response.status == 200 and json.loads(payload) == {
                    "id": document_id, "status": "confirmed",
                }
                setup_records.append({"task": index, "status": response.status,
                                      "seconds": time.perf_counter() - before,
                                      "valid": valid})
                if not valid:
                    raise RuntimeError("preconnection validation failed before measured workload")
                prepared[index] = connection
            setup_seconds = time.perf_counter() - setup_started
        with ThreadPoolExecutor(max_workers=N) as workers:
            tasks = list(workers.map(task, range(N)))
    records = [record for item in tasks for record in item["records"]]
    errors = [error for item in tasks for error in item["errors"]]
    task_seconds = [item["seconds"] for item in tasks]
    request_seconds = [record["seconds"] for record in records]
    return {
        "transport": "stdlib http.client; 200 threads; one socket per task; no retries",
        "connection_mode": connection_mode,
        "setup_requests": len(setup_records), "setup_seconds": setup_seconds,
        "setup_in_task_latency": connection_mode == "cold",
        "setup_records": setup_records,
        "total_http_requests": len(records) + len(setup_records),
        "expected_total_http_requests": 6 * N + len(setup_records),
        "concurrent_tasks": N, "completed_tasks": len(tasks),
        "successful_tasks": sum(item["success"] for item in tasks),
        "failed_tasks": sum(not item["success"] for item in tasks),
        "requests": len(records), "expected_requests": 6 * N,
        "error_count": len(errors), "errors": errors,
        "task_p50_seconds": percentile(task_seconds, .50),
        "task_p95_seconds": percentile(task_seconds, .95),
        "task_max_seconds": max(task_seconds),
        "request_p95_seconds": percentile(request_seconds, .95) if request_seconds else None,
        "elapsed_seconds": time.perf_counter() - released_at[0],
        "percentile_method": "nearest rank ceil(0.95*n); task clock starts at common barrier release",
        "task_latencies_seconds": task_seconds,
        "request_latencies_seconds": request_seconds,
        "request_records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=("stdlib", "async", "asgi"), default="stdlib")
    parser.add_argument("--connection-mode", choices=("cold", "preconnected"), default="cold",
                        help="stdlib only: cold includes connection setup; preconnected reports it separately")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).parent / "evidence/load-completion.json")
    options = parser.parse_args()
    if options.connection_mode != "cold" and options.transport != "stdlib":
        parser.error("--connection-mode preconnected requires --transport stdlib")
    with tempfile.TemporaryDirectory(prefix="vt044-load-") as temporary:
        root = Path(temporary)
        engine = create_engine(f"sqlite:///{root / 'load.db'}", pool_size=N, max_overflow=0,
                               connect_args={"check_same_thread": False, "timeout": 30})
        Base.metadata.create_all(engine)
        storage = LocalStorage(root / "files")
        now = datetime.now(timezone.utc)
        ids = [f"load-{index:04}" for index in range(N)]
        with Session(engine) as db:
            for index, document_id in enumerate(ids):
                stored = storage.save(f"Biểu mẫu {index}.png", f"synthetic-{index}".encode())
                db.add(Document(id=document_id, original_name=stored.original_name,
                                stored_name=stored.stored_name, mime_type="image/png",
                                size_bytes=stored.size_bytes, status="confirmed",
                                created_at=now, expires_at=now + timedelta(days=41)))
            db.flush()
            for index, document_id in enumerate(ids):
                db.add(Lifecycle(document_id=document_id, owner_id=f"user-{index}", deleted=False))
                db.add(Extraction(document_id=document_id, data={"index": index}, confirmed=True))
            db.commit()
        service = LifecycleService(engine, storage)
        app = create_app(service, {f"demo-{index}": f"user-{index}" for index in range(N)})
        if options.transport == "asgi":
            result = asyncio.run(exercise(0, ids, app=app))
        else:
            server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                sock.listen(2048)
                port = sock.getsockname()[1]
                thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
                thread.start()
                deadline = time.monotonic() + 10
                while not server.started:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("local server did not start")
                    threading.Event().wait(.01)
                try:
                    result = (exercise_stdlib(port, ids, connection_mode=options.connection_mode) if options.transport == "stdlib"
                              else asyncio.run(exercise(port, ids)))
                finally:
                    server.should_exit = True
                    thread.join(timeout=10)
        with Session(engine) as db:
            result["all_restored"] = not any(db.scalars(select(Lifecycle.deleted)))
            result["extraction_count"] = len(list(db.scalars(select(Extraction.id))))
            result["confirmed_documents"] = len(list(db.scalars(select(Document.id).where(Document.status == "confirmed"))))
            result["all_extractions_preserved"] = all(
                row.confirmed and row.data == {"index": index}
                for index, document_id in enumerate(ids)
                for row in [db.scalar(select(Extraction).where(Extraction.document_id == document_id))]
                if row is not None
            ) and result["extraction_count"] == N
        result["all_files_preserved"] = all(
            service.storage.resolve(name).read_bytes() == f"synthetic-{index}".encode()
            for index, name in _stored_names(engine, ids)
        )
        result["target_seconds"] = 5.0
        result["task_p95_meets_target"] = result["task_p95_seconds"] <= 5.0
        result["correctness_pass"] = (
            result["error_count"] == 0 and result["requests"] == 6 * N
            and result["all_restored"] and result["all_files_preserved"]
            and result["extraction_count"] == N and result["confirmed_documents"] == N
            and result["all_extractions_preserved"]
        )
        result["acceptance_pass"] = result["correctness_pass"] and result["task_p95_meets_target"]
        result["environment"] = {"python": platform.python_version(), "os": platform.system(), "machine": platform.machine(), "cpu": platform.processor()}
        result["scope"] = (
            ("in-process ASGI; no HTTP socket; " if options.transport == "asgi"
             else "one local uvicorn server; loopback HTTP; ")
            + "sync worker pool; file SQLite; 200 synthetic owners/documents; no OCR, gateway or browser"
        )
        if options.transport == "stdlib":
            result["scope"] += f"; connection_mode={options.connection_mode}; setup phase reported separately"
        engine.dispose()
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        summary = {key: value for key, value in result.items()
                   if "latencies" not in key and key not in ("request_records", "setup_records", "errors")}
        summary["error_sample"] = result["errors"][:1]
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if result["acceptance_pass"] else 1


def _stored_names(engine, ids):
    with Session(engine) as db:
        names = dict(db.execute(select(Document.id, Document.stored_name)).all())
    return [(index, names[document_id]) for index, document_id in enumerate(ids)]


if __name__ == "__main__":
    raise SystemExit(main())
