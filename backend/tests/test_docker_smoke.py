"""Host-side smoke guards. Native Docker evidence comes from the real smoke command."""

import importlib.util
import sys

import pytest

from docintel.config import ROOT


@pytest.fixture
def smoke():
    spec = importlib.util.spec_from_file_location(
        "docker_smoke", ROOT / "scripts/check_docker_smoke.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_readiness_wait_bounds_each_request_and_total_wait(smoke, monkeypatch):
    times = iter([0, 0, 91])
    monkeypatch.setattr(smoke.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(smoke.time, "sleep", lambda _: None)
    calls = []

    class Unready:
        def get(self, path, *, timeout):
            calls.append((path, timeout))
            return smoke.httpx.Response(503)

    with pytest.raises(RuntimeError, match="readiness timeout"):
        smoke.wait_ready(Unready())
    assert calls == [("/api/v1/readiness", 2)]


def test_readiness_accepts_ready_response(smoke):
    class Ready:
        def get(self, path, *, timeout):
            return smoke.httpx.Response(200)

    smoke.wait_ready(Ready())


def test_existing_report_is_preserved_before_docker_commands(smoke, tmp_path, monkeypatch):
    report = tmp_path / "existing.json"
    report.write_bytes(b"previous evidence")
    monkeypatch.setattr(sys, "argv", ["check_docker_smoke.py", "--output", str(report)])
    monkeypatch.setattr(
        smoke.subprocess, "run", lambda *_a, **_k: pytest.fail("Unexpected Docker command")
    )
    with pytest.raises(FileExistsError):
        smoke.main()
    assert report.read_bytes() == b"previous evidence"
