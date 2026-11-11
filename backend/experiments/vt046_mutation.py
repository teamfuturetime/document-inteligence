"""Kill a response-mapping mutant in a temporary package copy; source stays intact."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "backend/src/document_backend"
OLD = '        values[field] = normalized\n'
NEW = '        values[field] = values.get("invoice_number") if field == "seller_name" else normalized\n'


def main():
    with tempfile.TemporaryDirectory(prefix="vt046-mutant-") as directory:
        target = Path(directory) / "document_backend"
        shutil.copytree(SOURCE, target, ignore=shutil.ignore_patterns("__pycache__"))
        module = target / "services/validation.py"
        text = module.read_text()
        assert text.count(OLD) == 1, "Mutation location changed; review required"
        module.write_text(text.replace(OLD, NEW))
        env = {**os.environ, "PYTHONPATH": directory + os.pathsep + os.environ.get("PYTHONPATH", ""),
               "PYTHONDONTWRITEBYTECODE": "1"}
        # Prove the imported code is the isolated mutant, not the installed baseline.
        probe = subprocess.run([sys.executable, "-c", "import document_backend.services.validation as m; print(m.__file__)"],
                               cwd=ROOT, env=env, text=True, capture_output=True, check=True)
        assert str(target) in probe.stdout
        print("Mutated module:", probe.stdout.strip(), flush=True)
        print("Mutation: normalized_values.seller_name <- normalized invoice_number", flush=True)
        result = subprocess.run([sys.executable, "-m", "pytest", "backend/tests/test_notifications.py",
                                 "-k", "valid_result_survives_delivery_outcome", "-q"],
                                cwd=ROOT, env=env, text=True, capture_output=True)
        print(result.stdout)
        print(result.stderr)
        # Require assertion failures with both independent values in diff, not import errors.
        killed = (result.returncode == 1 and "3 failed" in result.stdout
                  and "AssertionError" in result.stdout and "VT046-17" in result.stdout
                  and "Cửa hàng Mây Việt" in result.stdout and "ModuleNotFoundError" not in result.stdout)
        print("MUTANT_KILLED=" + str(killed))
        return 0 if killed else 1


if __name__ == "__main__":
    raise SystemExit(main())
