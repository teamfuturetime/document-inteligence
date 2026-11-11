"""Invert a business rule on a disposable Git branch; never edit the source."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "individual/VT044/harness.py"


def main():
    original = SOURCE.read_bytes()
    with tempfile.TemporaryDirectory(prefix="vt044-mutant-") as directory:
        root = Path(directory)
        shutil.copytree(ROOT / "backend/app", root / "backend/app")
        target = root / "individual/VT044"
        target.mkdir(parents=True)
        for name in ("__init__.py", "harness.py", "test_lifecycle.py"):
            shutil.copy(ROOT / "individual/VT044" / name, target / name)
        shutil.copy(ROOT / "pyproject.toml", root / "pyproject.toml")

        def git(*args):
            return subprocess.check_output([
                "git", "-c", "user.name=VT044 experiment",
                "-c", "user.email=vt044@example.invalid", *args,
            ], cwd=root, text=True).strip()

        git("init", "-b", "mutation/vt044-invert-rule")
        git("add", ".")
        git("commit", "-m", "temporary clean harness snapshot")
        candidate = target / "harness.py"
        before = candidate.read_text()
        rule = "if state.deleted != target:"
        assert before.count(rule) == 1
        candidate.write_text(before.replace(rule, "if state.deleted == target:"))
        git("add", "individual/VT044/harness.py")
        git("commit", "-m", "MUTANT invert boolean transition business rule")
        print("temporary branch: mutation/vt044-invert-rule", flush=True)
        print("temporary mutant commit:", git("rev-parse", "HEAD"), flush=True)
        print(git("show", "--format=short", "--", "individual/VT044/harness.py"), flush=True)
        run = subprocess.run([
            sys.executable, "-m", "pytest", "-q",
            "individual/VT044/test_lifecycle.py::test_T01_T02_T03_state_cycle_preserves_related_data",
        ], cwd=root, text=True, capture_output=True)
        print(run.stdout, run.stderr, flush=True)
        killed = run.returncode == 1 and "FAILED" in run.stdout and "AssertionError" in run.stdout
        print(f"mutant_killed={killed}; pytest_exit={run.returncode}")
    unchanged = SOURCE.read_bytes() == original
    print("submission_source_unchanged=", unchanged)
    print("submission_source_sha256=", hashlib.sha256(original).hexdigest())
    return 0 if killed and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
