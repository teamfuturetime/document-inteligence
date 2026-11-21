"""Disposable process/HTTP lifecycle harness; no endpoints added to the product app."""

import argparse
import io
import json
import os
import queue
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from contextlib import asynccontextmanager
from http.cookiejar import CookieJar
from pathlib import Path

from docintel.config import ROOT, Settings

ORIGIN = "http://127.0.0.1:5173"
PASSWORD = "synthetic-lifecycle-password-123"


def emit(event, **values):
    print(json.dumps({"event": event, **values}), flush=True)


def child(runtime, auth_mode, gate, mode, worker_only=False, skip_worker_join=False):
    import uvicorn
    from docintel.api.app import create_app
    from docintel.services.documents import DocumentService
    from docintel.services.worker import LocalInferenceWorker

    if not (runtime / ".lifecycle-test-runtime").is_file():
        raise ValueError("Only a disposable lifecycle runtime is allowed")
    if skip_worker_join and mode != "fixture":
        raise ValueError("Mutation is restricted to explicit fixture tests")
    settings = Settings(
        _env_file=None,
        runtime_dir=runtime,
        auth_mode=auth_mode,
        provider_mode="tesseract",
        session_cookie_secure=False,
        cors_origins=[ORIGIN],
    )
    release = threading.Event()
    if gate == "none":
        release.set()
    if mode == "fixture":
        from test_product import inference

        DocumentService.ensure_ready = lambda _: {}
        real_pipeline = inference
    else:
        real_pipeline = None
    original_init = DocumentService.__init__
    original_cycle = DocumentService.process_next
    original_close = LocalInferenceWorker.close
    close_finished = threading.Event()

    def close_worker(self):
        emit("worker_closing", held=not release.is_set())
        if skip_worker_join:
            self.stop.set()  # Deliberate child-only regression: no join or lock release.
        else:
            original_close(self)
        close_finished.set()
        emit("worker_closed", alive=self.thread.is_alive())

    LocalInferenceWorker.close = close_worker

    def initialize(self, config):
        original_init(self, config)
        native = self.pipeline.run

        def pipeline(*args):
            emit("inference_started")
            if gate == "running" and not release.wait(20):
                raise TimeoutError("Lifecycle harness inference gate timeout")
            return (real_pipeline or native)(*args)

        self.pipeline.run = pipeline
        original_write = self.storage.write

        def write(*args):
            if gate == "upload" and args[1] == "source":
                emit("upload_started")
                if not release.wait(20):
                    raise TimeoutError("Lifecycle harness upload gate timeout")
            return original_write(*args)

        self.storage.write = write

    def cycle(self):
        if gate == "queued" and not release.is_set():
            return False
        done = original_cycle(self)
        if done:
            emit("cycle_finished")
        return done

    DocumentService.__init__ = initialize
    DocumentService.process_next = cycle
    if worker_only:
        worker = LocalInferenceWorker(DocumentService(settings))
        try:
            worker.start()
        except RuntimeError:
            emit("start_failed")
            return 2
        worker.close()
        emit("unexpected_worker_started")
        return 3
    app = create_app(settings)
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        async with original_lifespan(application):
            yield
            emit("lifespan_stopping")
        emit("lifespan_stopped")

    app.router.lifespan_context = lifespan

    class Server(uvicorn.Server):
        async def startup(self, sockets=None):
            try:
                await super().startup(sockets=sockets)
            except SystemExit:
                emit("start_failed")
                raise
            emit("ready", port=port) if self.started else emit("start_failed")

        async def shutdown(self, sockets=None):
            emit("shutdown_started")
            await super().shutdown(sockets=sockets)

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = Server(
        uvicorn.Config(
            app, log_level="critical", access_log=False, timeout_graceful_shutdown=15
        )
    )

    def control():
        for line in sys.stdin:
            command = line.strip()
            if command == "release":
                release.set()
            elif command == "hold":
                release.clear()
                emit("held")
            elif command == "stop":
                server.should_exit = True
            elif command == "observe-drain":
                # Observe actual close completion after the worker-close handshake;
                # this is a bounded event wait, not a sleep before shutdown starts.
                finished = close_finished.wait(0.5)
                emit(
                    "drain_observation", blocked=not finished, held=not release.is_set()
                )

    threading.Thread(target=control, daemon=True).start()
    try:
        server.run(sockets=[sock])
    finally:
        sock.close()
    return 0 if server.started else 2


class ProcessApp:
    def __init__(
        self,
        runtime,
        *,
        auth_mode="local",
        gate="running",
        mode="fixture",
        worker_only=False,
        skip_worker_join=False,
    ):
        self.pending = []
        self.events = queue.Queue()
        self.stderr_tail = deque(maxlen=40)
        args = [
            sys.executable,
            str(ROOT / "scripts/check_worker_lifecycle.py"),
            "--child",
            "--runtime",
            str(runtime),
            "--auth-mode",
            auth_mode,
            "--gate",
            gate,
            "--mode",
            mode,
        ]
        if worker_only:
            args.append("--worker-only")
        if skip_worker_join:
            args.append("--skip-worker-join")
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                str(ROOT / p) for p in ("backend/src", "pipeline/src", "backend/tests")
            ),
        }
        self.process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
            cwd=ROOT,
        )

        def read_stderr():
            for line in self.process.stderr:
                self.stderr_tail.append(line.rstrip()[-512:])

        self.stderr_reader = threading.Thread(target=read_stderr, daemon=True)
        self.stderr_reader.start()

        def read():
            for line in self.process.stdout:
                try:
                    self.events.put(json.loads(line))
                except ValueError:
                    continue
            self.events.put({"event": "eof"})

        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar())
        )
        self.csrf = None
        self.port = None

    def expect(self, event, timeout=15):
        for index, item in enumerate(self.pending):
            if item["event"] == event:
                return self.pending.pop(index)
        deadline = time.monotonic() + timeout
        while True:
            try:
                item = self.events.get(timeout=max(0.001, deadline - time.monotonic()))
            except queue.Empty as exc:
                raise self.handshake_failure(event, "timeout") from exc
            if item["event"] == event:
                return item
            if item["event"] == "eof":
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
                self.stderr_reader.join(timeout=1)
                raise self.handshake_failure(event, "process exited before handshake")
            self.pending.append(item)
            if time.monotonic() >= deadline:
                raise self.handshake_failure(event, "timeout")

    def handshake_failure(self, event, reason):
        return AssertionError(
            f"Lifecycle {reason}: {event}; exit={self.process.poll()}; "
            + "stderr tail:\n"
            + "\n".join(self.stderr_tail)
        )

    def ready(self):
        self.port = self.expect("ready")["port"]
        return self

    def command(self, command):
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def request(self, path, *, method="GET", data=None, headers=None):
        values = {"Origin": ORIGIN, **(headers or {})}
        if self.csrf:
            values["X-CSRF-Token"] = self.csrf
        if isinstance(data, dict):
            data = json.dumps(data).encode()
            values["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/v1" + path,
            data=data,
            method=method,
            headers=values,
        )
        try:
            response = self.opener.open(req, timeout=10)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.loads(response.read())

    def login(self, username="alpha"):
        status, state = self.request(
            "/auth/login",
            method="POST",
            data={"username": username, "password": PASSWORD},
            headers={"X-Requested-With": "docintel"},
        )
        assert status == 200
        self.csrf = state["csrf_token"]

    def stop(self):
        if os.name == "nt":
            self.command("stop")
        else:
            self.process.send_signal(signal.SIGTERM)
        self.expect("shutdown_started")

    def assert_worker_draining(self):
        try:
            assert self.expect("worker_closing")["held"]
            self.command("observe-drain")
            observed = self.expect("drain_observation")
        except (AssertionError, OSError, queue.Empty) as exc:
            raise AssertionError(
                "Worker shutdown returned before held inference was released"
            ) from exc
        assert observed["held"]
        assert observed["blocked"], (
            "Worker shutdown returned before held inference was released"
        )

    def wait_stopped(self):
        self.expect("lifespan_stopped")
        code = self.process.wait(timeout=10)
        # Uvicorn re-raises captured POSIX signals after lifespan cleanup.
        assert code == 0 if os.name == "nt" else code in {0, -signal.SIGTERM}
        return code

    def kill(self):
        self.process.kill()  # SIGKILL on POSIX; TerminateProcess on Windows.
        self.process.wait(timeout=5)

    def close(self):
        if self.process.poll() is None:
            try:
                self.command("release")
                self.command("stop")
                self.process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                self.kill()
        self.process.wait(timeout=5)
        self.reader.join(timeout=1)
        self.stderr_reader.join(timeout=1)
        try:
            self.process.stdin.close()
        except BrokenPipeError:
            pass  # The intentional no-join mutant can exit while a command is buffered.
        self.process.stdout.close()
        self.process.stderr.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def prepare_runtime(runtime, auth_mode="local"):
    from docintel.repositories.identity import IdentityRepository
    from docintel.repositories.sqlite import DocumentRepository
    from docintel.security import hash_password

    runtime.mkdir()
    (runtime / ".lifecycle-test-runtime").write_text("synthetic process harness only\n")
    if auth_mode == "session":
        repository = DocumentRepository(runtime / "documents.sqlite3")
        repository.initialize()
        identity = IdentityRepository(repository)
        for username in ("alpha", "beta"):
            identity.create_user(username, hash_password(PASSWORD))


def image():
    from PIL import Image

    stream = io.BytesIO()
    Image.new("RGB", (300, 200), "white").save(stream, format="PNG")
    return stream.getvalue()


def upload(app, data=None, key="lifecycle"):
    status, document = app.request(
        "/documents?document_type=hoa_don&data_origin=synthetic",
        method="POST",
        data=image() if data is None else data,
        headers={"Idempotency-Key": key},
    )
    assert status == 202
    return document


def native_smoke():
    with tempfile.TemporaryDirectory(prefix="docintel-native-lifecycle-") as directory:
        runtime = Path(directory) / "runtime"
        prepare_runtime(runtime)
        with ProcessApp(runtime, gate="running", mode="native") as app:
            app.ready()
            document = upload(
                app, (ROOT / "data/product/images/hoa_don_001.png").read_bytes()
            )
            app.expect("inference_started")
            app.command("release")
            app.expect("cycle_finished", timeout=40)
            status, detail = app.request("/documents/" + document["document_id"])
            assert status == 200 and detail["run"]["status"] == "succeeded"
            app.stop()
            app.wait_stopped()
        with ProcessApp(runtime, gate="queued", mode="native") as restarted:
            restarted.ready()
            assert (
                restarted.request("/documents/" + document["document_id"])[1] == detail
            )
    return {
        "status": "passed",
        "inference": "native",
        "checks": 3,
        "temporary_runtime": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--runtime", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--auth-mode",
        choices=["local", "session"],
        default="local",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--gate",
        choices=["queued", "running", "upload", "none"],
        default="running",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--mode",
        choices=["fixture", "native"],
        default="native",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--worker-only", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--skip-worker-join", action="store_true", help=argparse.SUPPRESS
    )
    args = parser.parse_args()
    if args.child:
        return child(
            args.runtime,
            args.auth_mode,
            args.gate,
            args.mode,
            args.worker_only,
            args.skip_worker_join,
        )
    print(json.dumps(native_smoke()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
