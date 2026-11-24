"""Metadata commands must never inherit a lifecycle controller's interactive stdin."""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from document_pipeline import provenance

ROOT = Path(__file__).resolve().parents[2]


def test_git_metadata_commands_are_noninteractive(monkeypatch):
    calls = []
    real_run = subprocess.run

    def run(argv, **kwargs):
        if argv[0] != "git":
            return real_run(argv, **kwargs)  # platform.processor may invoke uname on POSIX.
        assert kwargs.get("stdin") == subprocess.DEVNULL
        assert kwargs["timeout"] == 2 and kwargs["capture_output"]
        assert not kwargs.get("shell", False)
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, b"a" * 40 if argv[1] == "rev-parse" else b"")

    monkeypatch.setattr(provenance.subprocess, "run", run)
    result = provenance.runtime_metadata()
    assert [args[1] for args in calls] == ["rev-parse", "status"]
    assert result["git_commit"] == "a" * 40 and result["git_dirty"] is False


def test_real_git_metadata_finishes_while_control_pipe_reader_is_blocked():
    expected = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
        timeout=2,
    ).stdout.strip()
    code = """
import json, sys, threading
from document_pipeline.provenance import runtime_metadata
started = threading.Event()
finished = threading.Event()
commands = []
def control():
    started.set()
    commands.append(sys.stdin.readline().strip())
    finished.set()
threading.Thread(target=control, daemon=True).start()
assert started.wait(2)
print(json.dumps(runtime_metadata()), flush=True)
assert finished.wait(10) and commands == ['quit']
"""
    process = subprocess.Popen(
        [sys.executable, "-c", code],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        output = pool.submit(process.stdout.readline)
        try:
            metadata = json.loads(output.result(timeout=10))
            assert metadata["git_commit"] == expected
            assert len(metadata["pipeline_source_sha256"]) == 64
            process.stdin.write("quit\n")
            process.stdin.flush()
            assert process.wait(timeout=5) == 0, process.stderr.read()
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
