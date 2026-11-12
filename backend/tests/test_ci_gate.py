"""Execute the actual Actions gate: no skipped/failed/cancelled job may look green."""

import json
import os
import re
import subprocess
import sys

import pytest
import yaml

from docintel.config import ROOT


@pytest.mark.parametrize("outcome", ["success", "failure", "skipped", "cancelled", "missing"])
def test_product_gate_requires_every_result(outcome):
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    gate = workflow["jobs"]["product-checks"]
    assert "always()" in gate["if"]
    results = {job: {"result": "success"} for job in gate["needs"]}
    assert len(results) == 5
    if outcome == "missing":
        results.pop("browser-e2e")
    else:
        results["browser-e2e"]["result"] = outcome
    script = re.fullmatch(r"python3 - <<'PY'\n(.*?)\nPY\n", gate["steps"][0]["run"], re.S)
    assert script is not None, "Gate script structure changed; review the executable test"
    result = subprocess.run(
        [sys.executable, "-c", script.group(1)],
        env={**os.environ, "JOB_RESULTS": json.dumps(results)},
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == (0 if outcome == "success" else 1)
    if outcome != "success":
        assert "Product checks blocked:" in result.stderr
