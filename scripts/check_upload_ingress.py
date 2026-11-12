"""Real loopback HTTP ingress probe (POSIX); no OCR or model accuracy measurement."""

import argparse
import asyncio
import http.client
import json
import resource
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path

from docintel.config import ROOT, Settings

UPLOAD_PATH = "/api/v1/documents?document_type=hoa_don&data_origin=synthetic"
MAXIMUM = 5_242_880
TIMEOUT = 0.5
SLOTS = 2


def serve(fd, runtime):
    import uvicorn
    from docintel.api.app import create_app

    app = create_app(
        Settings(
            _env_file=None,
            runtime_dir=runtime,
            provider_mode="unconfigured",
            max_upload_bytes=MAXIMUM,
            upload_receive_timeout_seconds=TIMEOUT,
            max_concurrent_uploads=SLOTS,
        ),
        start_worker=False,
    )

    @app.get("/probe/metrics", include_in_schema=False)
    async def metrics():
        service = app.state.documents
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return {
            "rss_high_water_bytes": peak if sys.platform == "darwin" else peak * 1024,
            "asyncio_tasks": len(asyncio.all_tasks()),
            "active_uploads": app.state.upload_limiter.borrowed_tokens,
            "documents": service.list_documents(1, 0).total,
            "source_preview_files": len(list(service.storage.root.iterdir())),
        }

    server = uvicorn.Server(
        uvicorn.Config(app, log_level="warning", limit_concurrency=16)
    )
    server.run(sockets=[socket.socket(fileno=fd)])


def get_metrics(port):
    with closing(
        http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    ) as connection:
        connection.request("GET", "/probe/metrics")
        response = connection.getresponse()
        assert response.status == 200
        return json.loads(response.read())


def open_upload(port, *, length=None, chunked=False):
    connection = socket.create_connection(("127.0.0.1", port), timeout=3)
    headers = [f"POST {UPLOAD_PATH} HTTP/1.1", "Host: localhost", "Connection: close"]
    if length is not None:
        headers.append(f"Content-Length: {length}")
    if chunked:
        headers.append("Transfer-Encoding: chunked")
    connection.sendall(("\r\n".join(headers) + "\r\n\r\n").encode())
    return connection


def read_response(connection):
    response = http.client.HTTPResponse(connection)
    response.begin()
    payload = json.loads(response.read())
    return response.status, payload["error"]["code"]


def probe(port):
    samples = {"idle": get_metrics(port)}
    results = []

    def check(name, connection, started, expected):
        try:
            actual = read_response(connection)
            assert actual == expected, (name, actual, expected)
            results.append(
                {
                    "case": name,
                    "status": actual[0],
                    "code": actual[1],
                    "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
                }
            )
        finally:
            connection.close()

    start = time.monotonic()
    check(
        "declared_oversize_no_body",
        open_upload(port, length=MAXIMUM + 1),
        start,
        (413, "FILE_TOO_LARGE"),
    )
    start = time.monotonic()
    connection = open_upload(port, chunked=True)
    # Legal HTTP framing, but a decoded body one byte beyond the application cap.
    chunk = b"x" * (MAXIMUM + 1)
    connection.sendall(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n0\r\n\r\n")
    check("chunked_oversize", connection, start, (413, "FILE_TOO_LARGE"))

    start = time.monotonic()
    first = open_upload(port, length=100)
    first.sendall(b"x")
    second = open_upload(port, length=100)
    second.sendall(b"x")
    deadline = time.monotonic() + 0.3
    while (active := get_metrics(port))["active_uploads"] != SLOTS:
        assert time.monotonic() < deadline, active
        time.sleep(0.005)
    samples["two_slow_uploads"] = active
    rejection_start = time.monotonic()
    check(
        "admission_full_no_body",
        open_upload(port, length=100),
        rejection_start,
        (429, "UPLOAD_BUSY"),
    )
    # Supply additional chunks below the deadline; the total deadline must still fire.
    time.sleep(0.15)
    first.sendall(b"x")
    second.sendall(b"x")
    check("slow_body_total_deadline_1", first, start, (408, "UPLOAD_TIMEOUT"))
    check("slow_body_total_deadline_2", second, start, (408, "UPLOAD_TIMEOUT"))

    connection = open_upload(port, length=100)
    connection.sendall(b"partial")
    connection.close()
    deadline = time.monotonic() + 2
    while (recovered := get_metrics(port))["active_uploads"]:
        assert time.monotonic() < deadline, recovered
        time.sleep(0.01)
    samples["after_disconnect"] = recovered

    # A complete request reaches the unchanged provider check after all rejections.
    start = time.monotonic()
    connection = open_upload(port, length=1)
    connection.sendall(b"x")
    check(
        "slot_reused_provider_unconfigured",
        connection,
        start,
        (503, "PROVIDER_UNAVAILABLE"),
    )
    samples["final"] = get_metrics(port)
    assert all(
        s["documents"] == s["source_preview_files"] == 0 for s in samples.values()
    )
    assert samples["final"]["active_uploads"] == 0
    return {"cases": results, "server_samples": samples}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "runtime/verification/upload-ingress.json"
    )
    parser.add_argument("--serve-fd", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--runtime-dir", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve_fd is not None:
        serve(args.serve_fd, args.runtime_dir)
        return
    if args.output.exists():
        parser.error(
            "Output already exists; choose a new path to preserve earlier measurements."
        )
    with (
        tempfile.TemporaryDirectory(prefix="docintel-ingress-") as temporary,
        socket.socket() as listener,
        (Path(temporary) / "server.log").open("wb") as log,
    ):
        listener.bind(("127.0.0.1", 0))
        listener.listen(64)
        port = listener.getsockname()[1]
        process = subprocess.Popen(
            [
                sys.executable,
                __file__,
                "--serve-fd",
                str(listener.fileno()),
                "--runtime-dir",
                str(Path(temporary) / "app"),
            ],
            cwd=ROOT,
            pass_fds=(listener.fileno(),),
            stdout=log,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    get_metrics(port)
                    break
                except (OSError, http.client.HTTPException):
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError(Path(log.name).read_text()) from None
                    time.sleep(0.05)
            report = probe(port)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
