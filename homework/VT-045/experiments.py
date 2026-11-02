"""Reproduce VT-045 evidence. Run from repo root with its .venv Python."""

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "homework/VT-045/evidence"
PYTHON = sys.executable
TEST = "backend/tests/test_invoice_policy.py"
BASELINE = "52067697c1e4505eb36042e5fbe525ed984d2637"


def execute(command, *, cwd=ROOT, env=None):
    return subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")


def save_run(name, command, *, cwd=ROOT, env=None):
    p = execute(command, cwd=cwd, env=env)
    (EVIDENCE / f"{name}.txt").write_text(
        "UTC: " + datetime.now(timezone.utc).isoformat() + "\nCOMMAND: " + " ".join(map(str, command))
        + "\nEXIT: " + str(p.returncode) + "\n" + p.stdout + p.stderr, encoding="utf-8")
    print(name, "exit", p.returncode, p.stdout[-250:])
    return p


def regression():
    command = [PYTHON, "-m", "coverage", "run", "--branch", "--source=backend/app",
               "--data-file=" + str(EVIDENCE / ".coverage"), "-m", "pytest", "-c", "backend/pytest.ini", "backend/tests", "-q"]
    p = save_run("green", command)
    if p.returncode:
        raise RuntimeError("Regression failed; see green.txt")
    for arguments in [["json", "-o", str(EVIDENCE / "coverage.json")], ["report", "-m"]]:
        result = save_run("coverage" if arguments[0] == "report" else "coverage-export",
                          [PYTHON, "-m", "coverage", *arguments, "--data-file=" + str(EVIDENCE / ".coverage")])
        if result.returncode:
            raise RuntimeError("Coverage export failed")


def repeat():
    results = []
    for i, seed in enumerate(["1", "17", "2026", "1", "17"], 1):
        env = {**os.environ, "PYTHONHASHSEED": seed, "TZ": "UTC" if i % 2 else "Asia/Ho_Chi_Minh"}
        command = [PYTHON, "-m", "pytest", "-c", "backend/pytest.ini", TEST, "-q"]
        p = save_run(f"repeat-{i}", command, env=env)
        results.append({"iteration": i, "hash_seed": seed, "TZ": env["TZ"], "exit": p.returncode})
    (EVIDENCE / "repeat.json").write_text(json.dumps({"runs": results, "note":
        "Windows TZ env alone does not prove timezone conversion. Service has no clock calls; tc11 forbids clock/sleep/random/network, tc10 checks reversed order and concurrent independent policies."}, indent=2), encoding="utf-8")
    if any(r["exit"] for r in results):
        raise RuntimeError("Flaky repeat failed")


def mutate():
    # A real temporary Git commit, isolated from the submission branch.
    with tempfile.TemporaryDirectory(prefix="vt045-mutation-") as base:
        target = Path(base).resolve() / "worktree"
        assert target.is_relative_to(Path(tempfile.gettempdir()).resolve())
        command = ["git", "worktree", "add", "--detach", str(target), "HEAD"]
        p = execute(command)
        if p.returncode:
            raise RuntimeError(p.stderr)
        try:
            source = target / "backend/app/services/invoice_policy.py"
            original = source.read_text(encoding="utf-8")
            good = 'raise InvoicePolicyError("Invoice policy is unavailable or invalid") from exc'
            bad = 'return InvoicePolicy(policy_version="invoice-policy-1", max_total_amount=MAX_SAFE_INTEGER)'
            assert original.count(good) == 1
            source.write_text(original.replace(good, bad), encoding="utf-8")
            for cmd in [["git", "add", "backend/app/services/invoice_policy.py"],
                        ["git", "commit", "-m", "experiment(vt045): swallow policy exception and return defaults"]]:
                p = execute(cmd, cwd=target)
                if p.returncode:
                    raise RuntimeError(p.stderr)
            mutation_hash = execute(["git", "rev-parse", "HEAD"], cwd=target).stdout.strip()
            (EVIDENCE / "mutation.patch").write_text(execute(["git", "show", "--format=fuller", "HEAD"], cwd=target).stdout, encoding="utf-8")
            nodes = [TEST + "::test_tc05_read_failure_is_not_swallowed", TEST + "::test_tc09_http_contract_business_rejection_and_failure"]
            p = save_run("mutation", [PYTHON, "-m", "pytest", "-c", "backend/pytest.ini", *nodes, "-q"], cwd=target)
            killed = p.returncode == 1 and "2 failed" in p.stdout and "ERROR collecting" not in p.stdout
            (EVIDENCE / "mutation.json").write_text(json.dumps({
                "base_commit": execute(["git", "rev-parse", "HEAD"]).stdout.strip(),
                "temporary_commit": mutation_hash, "mutation": "swallow exception and return default policy",
                "test_exit": p.returncode, "killed": killed, "tests": nodes,
                "scope": "One prescribed non-equivalent manual mutation, not an exhaustive mutation score",
            }, indent=2), encoding="utf-8")
            if not killed:
                raise RuntimeError("Mutation survived or did not fail for expected assertions")
        finally:
            assert target.resolve().is_relative_to(Path(base).resolve())
            p = execute(["git", "worktree", "remove", "--force", str(target)])
            if p.returncode:
                raise RuntimeError(p.stderr)


async def load_round(base_url, count=100):
    import httpx2
    gate = asyncio.Event()
    raw = {"invoice_number": "0000123", "invoice_date": "03/04/2026", "seller_name": "Cửa hàng Mây Việt", "currency": "VND"}
    expected = {**raw, "invoice_date": "2026-04-03"}
    async with httpx2.AsyncClient(base_url=base_url, trust_env=False, timeout=15,
                                 limits=httpx2.Limits(max_connections=count, max_keepalive_connections=count)) as client:
        async def request(i):
            amount = 99999 if i % 2 == 0 else 100001
            await gate.wait()
            start = time.perf_counter()
            try:
                response = await client.post("/validate", json={**raw, "total_amount": amount})
                latency = time.perf_counter() - start
                body = response.json()
                values = {**expected, "total_amount": amount if i % 2 == 0 else None}
                errors = [] if i % 2 == 0 else [{"field": "total_amount", "code": "business.amount_exceeds_policy", "message": "Amount exceeds the configured acceptance ceiling"}]
                oracle = body == {"valid": i % 2 == 0, "normalized_values": values, "errors": errors, "warnings": []}
                return {"task": i, "seconds": latency, "status": response.status_code,
                        "outcome_correct": response.status_code == 200 and oracle}
            except Exception as exc:
                return {"task": i, "seconds": time.perf_counter() - start, "error_type": type(exc).__name__, "outcome_correct": False}
        tasks = [asyncio.create_task(request(i)) for i in range(count)]
        await asyncio.sleep(0)  # let all 100 wait on the start barrier
        started = time.perf_counter()
        gate.set()
        rows = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - started
    ordered = sorted(row["seconds"] for row in rows)
    p95 = ordered[math.ceil(.95 * count) - 1]
    return {"tasks": count, "p50_seconds": ordered[math.ceil(.50 * count) - 1],
            "p95_seconds": p95, "max_seconds": ordered[-1], "batch_seconds": elapsed,
            "throughput_rps": count / elapsed, "correct_outcomes": sum(row["outcome_correct"] for row in rows),
            "meets_target": p95 <= 3 and all(row["outcome_correct"] for row in rows), "requests": rows}


def load():
    import httpx2
    with tempfile.TemporaryDirectory(prefix="vt045-load-") as temp:
        policy = Path(temp) / "policy.json"
        policy.write_text(json.dumps({"policy_version": "invoice-policy-1", "max_total_amount": 100000}), encoding="utf-8")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
        cmd = [PYTHON, str(ROOT / "homework/VT-045/harness.py"), "--policy", str(policy), "--port", str(port)]
        with (EVIDENCE / "load-server.txt").open("w", encoding="utf-8") as log:
            server = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=log,
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                base_url = f"http://127.0.0.1:{port}"
                deadline = time.monotonic() + 15
                with httpx2.Client(trust_env=False, timeout=1) as client:
                    while True:
                        try:
                            if client.get(base_url + "/ready").status_code == 200:
                                break
                        except httpx2.HTTPError:
                            pass
                        if server.poll() is not None or time.monotonic() > deadline:
                            raise RuntimeError("Harness server did not become ready")
                        time.sleep(.05)
                rounds = [asyncio.run(load_round(base_url)) for _ in range(3)]
                result = {"utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
                          "platform": platform.platform(), "cpu_count": os.cpu_count(),
                          "httpx2": httpx2.__version__, "concurrency": 100, "target_p95_seconds": 3,
                          "policy_sha256": hashlib.sha256(policy.read_bytes()).hexdigest(), "rounds": rounds,
                          "all_rounds_meet_target": all(r["meets_target"] for r in rounds),
                          "scope": "Real loopback HTTP, one Uvicorn process, sync validation in default ASGI threadpool; 100 simultaneous client tasks, 50 accepts and 50 rejects per round. No OCR/VLM, browser, WAN, sustained soak or production claim."}
                (EVIDENCE / "load.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
                print(json.dumps({k: v for k, v in result.items() if k != "rounds"}, indent=2))
                for i, r in enumerate(rounds, 1):
                    print("round", i, {k: v for k, v in r.items() if k != "requests"})
                if not result["all_rounds_meet_target"]:
                    raise RuntimeError("Load target or business oracle failed")
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", choices=["regression", "repeat", "mutate", "load"])
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    globals()[args.experiment]()
