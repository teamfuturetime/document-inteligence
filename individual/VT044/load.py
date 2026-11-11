"""200 barrier-released tasks over actual loopback HTTP; synthetic documents."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
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


async def exercise(port, ids):
    gate = asyncio.Event()
    request_seconds, task_seconds, errors = [], [], []
    limits = httpx.Limits(max_connections=N, max_keepalive_connections=N)
    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", limits=limits, timeout=30) as client:
        async def task(index):
            headers = {"X-API-Key": f"demo-{index}"}
            path = f"/documents/{ids[index]}"
            await gate.wait()
            started = time.perf_counter()
            steps = [
                ("DELETE", path, 200), ("GET", path, 404),
                ("GET", f"/documents/{ids[(index + 1) % N]}", 404),
                ("POST", path + "/restore", 200), ("GET", path, 200),
                ("GET", path + "/content", 200),
            ]
            try:
                for method, url, expected in steps:
                    before = time.perf_counter()
                    response = await client.request(method, url, headers=headers)
                    request_seconds.append(time.perf_counter() - before)
                    if response.status_code != expected:
                        errors.append({"task": index, "method": method, "expected": expected, "actual": response.status_code})
                    elif url.endswith("/content") and response.content != f"synthetic-{index}".encode():
                        errors.append({"task": index, "problem": "wrong content"})
            except Exception as error:
                errors.append({"task": index, "exception": type(error).__name__, "traceback": traceback.format_exc()})
            finally:
                task_seconds.append(time.perf_counter() - started)

        pending = [asyncio.create_task(task(index)) for index in range(N)]
        await asyncio.sleep(0)  # All tasks reach the gate; no artificial timed sleep.
        started = time.perf_counter()
        gate.set()
        await asyncio.gather(*pending)
        elapsed = time.perf_counter() - started
    return {
        "concurrent_tasks": N, "completed_tasks": len(task_seconds),
        "requests": len(request_seconds), "expected_requests": 6 * N,
        "error_count": len(errors), "errors": errors,
        "task_p50_seconds": percentile(task_seconds, .50),
        "task_p95_seconds": percentile(task_seconds, .95),
        "task_max_seconds": max(task_seconds),
        "request_p95_seconds": percentile(request_seconds, .95) if request_seconds else None,
        "elapsed_seconds": elapsed,
        "percentile_method": "nearest rank ceil(0.95*n)",
        "task_latencies_seconds": task_seconds,
        "request_latencies_seconds": request_seconds,
    }


def main():
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
                result = asyncio.run(exercise(port, ids))
            finally:
                server.should_exit = True
                thread.join(timeout=10)
        with Session(engine) as db:
            result["all_restored"] = not any(db.scalars(select(Lifecycle.deleted)))
            result["extraction_count"] = len(list(db.scalars(select(Extraction.id))))
            result["confirmed_documents"] = len(list(db.scalars(select(Document.id).where(Document.status == "confirmed"))))
        result["all_files_preserved"] = all(
            service.storage.resolve(name).read_bytes() == f"synthetic-{index}".encode()
            for index, name in _stored_names(engine, ids)
        )
        result["target_seconds"] = 5.0
        result["task_p95_meets_target"] = result["task_p95_seconds"] <= 5.0
        result["environment"] = {"python": platform.python_version(), "os": platform.system(), "machine": platform.machine(), "cpu": platform.processor()}
        result["scope"] = "one local uvicorn server; sync worker pool; file SQLite; 200 synthetic owners/documents; no OCR, gateway or browser"
        engine.dispose()
        output = Path(__file__).parent / "evidence/load.json"
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(json.dumps({key: value for key, value in result.items() if "latencies" not in key}, indent=2, ensure_ascii=False))
        return 0 if result["error_count"] == 0 and result["requests"] == 6 * N and result["all_restored"] and result["all_files_preserved"] else 1


def _stored_names(engine, ids):
    with Session(engine) as db:
        names = dict(db.execute(select(Document.id, Document.stored_name)).all())
    return [(index, names[document_id]) for index, document_id in enumerate(ids)]


if __name__ == "__main__":
    raise SystemExit(main())
