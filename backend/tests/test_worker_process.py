"""Real process/HTTP/SQLite tests with explicit inference doubles and pipe handshakes."""

import importlib.util
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from docintel.config import ROOT


@pytest.fixture
def harness():
    spec = importlib.util.spec_from_file_location(
        "lifecycle_harness", ROOT / "scripts/check_worker_lifecycle.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def connect(runtime):
    return closing(
        sqlite3.connect(
            (runtime / "documents.sqlite3").resolve().as_uri() + "?mode=ro", uri=True, timeout=1
        )
    )


def run_state(runtime, run_id):
    with connect(runtime) as db:
        return db.execute("SELECT status,error_code FROM runs WHERE run_id=?", (run_id,)).fetchone()


@pytest.mark.parametrize("auth_mode", ["local", "session"])
@pytest.mark.parametrize("phase", ["queued", "running"])
def test_crash_releases_locks_and_only_restart_recovers(runtime_dir, harness, auth_mode, phase):
    runtime = runtime_dir
    harness.prepare_runtime(runtime, auth_mode)
    with harness.ProcessApp(runtime, auth_mode=auth_mode, gate=phase) as app:
        app.ready()
        if auth_mode == "session":
            app.login()
        document = harness.upload(app)
        run_id = document["run"]["run_id"]
        if phase == "running":
            app.expect("inference_started")
        assert run_state(runtime, run_id) == (phase, None)
        for worker_only in (False, True):
            with harness.ProcessApp(
                runtime, auth_mode=auth_mode, worker_only=worker_only
            ) as rejected:
                rejected.expect("start_failed")
                rejected.process.wait(timeout=5)
                assert rejected.process.returncode != 0
            assert run_state(runtime, run_id) == (phase, None)
        with connect(runtime) as db:
            assert db.execute(
                "SELECT count(*) FROM events WHERE action='interrupted'"
            ).fetchone() == (0,)
        app.kill()
    with harness.ProcessApp(runtime, auth_mode=auth_mode, gate="running") as restarted:
        restarted.ready()
        if auth_mode == "session":
            restarted.login()
        if phase == "running":
            assert run_state(runtime, run_id) == ("failed", "PROCESSING_INTERRUPTED")
            _, detail = restarted.request("/documents/" + document["document_id"])
            assert detail["review"] is None
            with connect(runtime) as db:
                assert db.execute(
                    "SELECT count(*) FROM events WHERE action='interrupted'"
                ).fetchone() == (1,)
        else:
            restarted.expect("inference_started")
            assert run_state(runtime, run_id) == ("running", None)
            restarted.command("release")
            restarted.expect("cycle_finished")
            assert run_state(runtime, run_id) == ("succeeded", None)
            assert (
                restarted.request("/documents/" + document["document_id"])[1]["review"][
                    "review_status"
                ]
                == "draft"
            )
        if auth_mode == "session":
            restarted.login("beta")
            assert restarted.request("/documents/" + document["document_id"])[0] == 404
            assert restarted.request("/documents")[1]["total"] == 0


@pytest.fixture
def runtime_dir(tmp_path):
    return tmp_path / "runtime"


@pytest.mark.parametrize("auth_mode", ["local", "session"])
def test_completed_confirmed_export_survives_later_process_crash(runtime_dir, harness, auth_mode):
    runtime = runtime_dir
    harness.prepare_runtime(runtime, auth_mode)
    with harness.ProcessApp(runtime, auth_mode=auth_mode) as app:
        app.ready()
        if auth_mode == "session":
            app.login()
        document = harness.upload(app, key="confirmed")
        app.expect("inference_started")
        app.command("release")
        app.expect("cycle_finished")
        path = "/documents/" + document["document_id"]
        request = {"run_id": document["run"]["run_id"], "expected_revision": 1}
        status, confirmed = app.request(path + "/confirm", method="POST", data=request)
        assert status == 200
        export_path = path + "/export?run_id=" + request["run_id"] + "&revision=1"
        before = app.request(export_path)[1]
        before.pop("exported_at")
        history = app.request(path + "/history")[1]
        source = (runtime / "documents" / (document["document_id"] + ".source")).read_bytes()
        app.command("hold")
        app.expect("held")
        other = harness.upload(app, key="crash-after-confirm")
        app.expect("inference_started")
        app.kill()
    with harness.ProcessApp(runtime, auth_mode=auth_mode, gate="queued") as restarted:
        restarted.ready()
        if auth_mode == "session":
            restarted.login()
        assert restarted.request(path)[1] == confirmed
        assert restarted.request(path + "/history")[1] == history
        after = restarted.request(export_path)[1]
        after.pop("exported_at")
        assert after == before
        assert (
            runtime / "documents" / (document["document_id"] + ".source")
        ).read_bytes() == source
        assert run_state(runtime, other["run"]["run_id"]) == ("failed", "PROCESSING_INTERRUPTED")


@pytest.mark.parametrize("phase", ["upload", "running"])
def test_graceful_stop_waits_for_inflight_work_then_next_start_is_consistent(
    runtime_dir, harness, phase
):
    runtime = runtime_dir
    harness.prepare_runtime(runtime)
    with harness.ProcessApp(runtime, gate=phase) as app:
        app.ready()
        with ThreadPoolExecutor(max_workers=1) as pool:
            request = pool.submit(harness.upload, app)
            try:
                app.expect("upload_started" if phase == "upload" else "inference_started")
                app.stop()
                assert app.process.poll() is None
                if phase == "upload":
                    assert not request.done()
                else:
                    app.assert_worker_draining()
                app.command("release")
                document = request.result(timeout=10)
                if phase == "running":
                    app.expect("cycle_finished")
                    assert not app.expect("worker_closed")["alive"]
                app.wait_stopped()
            finally:
                if app.process.poll() is None:
                    app.command("release")
    with harness.ProcessApp(runtime, gate="queued") as restarted:
        restarted.ready()
        status, detail = restarted.request("/documents/" + document["document_id"])
        assert status == 200
        assert detail["run"]["status"] in {"queued", "succeeded"}
        if phase == "running":
            assert detail["run"]["status"] == "succeeded"
        assert (
            runtime / "documents" / (document["document_id"] + ".source")
        ).read_bytes() == harness.image()


def test_graceful_oracle_rejects_child_mutation_that_skips_join(runtime_dir, harness):
    runtime = runtime_dir
    harness.prepare_runtime(runtime)
    with harness.ProcessApp(runtime, gate="running", skip_worker_join=True) as app:
        app.ready()
        document = harness.upload(app)
        app.expect("inference_started")
        app.stop()
        with pytest.raises(AssertionError, match="shutdown returned"):
            app.assert_worker_draining()  # Same oracle as the authored graceful test.
        assert run_state(runtime, document["run"]["run_id"])[0] == "running"


def test_failed_child_handshake_includes_bounded_stderr(runtime_dir, harness, monkeypatch):
    popen = harness.subprocess.Popen

    def failing_child(_args, **kwargs):
        return popen(
            [
                sys.executable,
                "-c",
                "import sys; print('SYNTHETIC_CHILD_ERROR', file=sys.stderr); sys.exit(2)",
            ],
            **kwargs,
        )

    monkeypatch.setattr(harness.subprocess, "Popen", failing_child)
    with harness.ProcessApp(runtime_dir) as app:
        with pytest.raises(AssertionError, match="SYNTHETIC_CHILD_ERROR") as failure:
            app.ready()
        assert "exit=2" in str(failure.value)
        assert len(str(failure.value)) < 40 * 512 + 256
