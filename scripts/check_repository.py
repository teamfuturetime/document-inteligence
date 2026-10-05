"""Kiểm tra links/docs, config và cấu trúc workflow local; không xác minh remote CI/Docker."""

import json
import re
import subprocess
from urllib.parse import unquote

import yaml
from docintel.config import ROOT

files = (
    subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
    )
    .decode("utf-8")
    .split("\0")
)
markdown_paths = [ROOT / path for path in files if path.endswith(".md")]
errors = []
for path in markdown_paths:
    source = path.read_text(encoding="utf-8")
    for destination in re.findall(r"\[[^\]]*\]\(([^)]+)\)", source):
        destination = destination.strip().split("#", 1)[0]
        if not destination or re.match(r"^[a-z]+:", destination):
            continue
        target = (path.parent / unquote(destination)).resolve()
        if not target.exists() or not target.is_relative_to(ROOT):
            errors.append(f"Broken link: {path.relative_to(ROOT)} -> {destination}")
config = json.loads((ROOT / "configs/foundation.json").read_text(encoding="utf-8"))
if config["provider"] != "fixture" or config["purpose"] != "contract_fixture":
    errors.append("Foundation config must be fixture only")
workflow = yaml.safe_load(
    (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
)
if workflow["permissions"] != {"contents": "read"}:
    errors.append("CI permissions are not minimal")
if set(workflow["jobs"]) != {"backend-checks", "frontend-checks"}:
    errors.append("CI required check names drift")
for job in workflow["jobs"].values():
    for step in job["steps"]:
        if "uses" in step and not re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"]):
            errors.append("Unpinned Action ref")
        if "continue-on-error" in step or "continue-on-error" in job:
            errors.append("CI masks failures")
for name in ("bug", "feature", "data-model-error"):
    form = yaml.safe_load(
        (ROOT / f".github/ISSUE_TEMPLATE/{name}.yml").read_text(encoding="utf-8")
    )
    if "labels" in form or "assignees" in form or not form.get("body"):
        errors.append("Issue form needs labels/accounts not configured")
compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
for service in compose["services"].values():
    if not all(port.startswith("127.0.0.1:") for port in service.get("ports", [])):
        errors.append("Compose exposes non-loopback ports")
if (ROOT / "LICENSE").exists() or (ROOT / ".github/CODEOWNERS").exists():
    errors.append("Confirm human license/handles before activating these files")
if errors:
    raise SystemExit("\n".join(errors))
print(
    f"Repository CHECK PASS: {len(markdown_paths)} Markdown files, config/YAML/Action refs."
)
