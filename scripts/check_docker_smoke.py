"""Real Compose native OCR smoke on fresh project-scoped volumes, with bounded cleanup."""

import argparse
import hashlib
import io
import json
import subprocess
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx2 as httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def request(api, method, path, status=200, **kwargs):
    response = api.request(method, path, **kwargs)
    assert response.status_code == status, (
        method,
        path,
        response.status_code,
        response.text[:300],
    )
    return response.json()


def wait_ready(api):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            if api.get("/api/v1/readiness", timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError("Compose readiness timeout")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    project = "docintel52-" + uuid.uuid4().hex
    report = {
        "project": project,
        "status": "failed",
        "checked_at": datetime.now(UTC).isoformat(),
        "checks": [],
        "head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_hashes": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                ".dockerignore",
                "backend/Dockerfile",
                "frontend/Dockerfile",
                "compose.yaml",
                "scripts/check_docker_smoke.py",
                "scripts/docker_volume_probe.py",
            )
        },
    }
    with tempfile.TemporaryDirectory(prefix="docintel52-config-") as directory:
        config = Path(directory) / "override.yaml"
        config.write_text(
            "services:\n  backend:\n    ports: !reset []\n    environment:\n      DOCINTEL_AUTH_MODE: local\n    volumes:\n"
            + f"      - {json.dumps(str(ROOT / 'scripts') + ':/qa:ro')}\n"
            + '      - qa-state:/qa-state\n  frontend:\n    ports: !override ["127.0.0.1::80"]\nvolumes:\n  qa-state:\n',
            encoding="utf-8",
        )
        env = Path(directory) / "empty.env"
        env.touch()
        compose = [
            "docker",
            "compose",
            "--env-file",
            str(env),
            "--project-directory",
            str(ROOT),
            "-p",
            project,
            "-f",
            str(ROOT / "compose.yaml"),
            "-f",
            str(config),
        ]

        def run(*command, capture=False):
            result = subprocess.run(
                [*compose, *command],
                cwd=ROOT,
                check=True,
                text=True,
                stdout=subprocess.PIPE if capture else None,
            )
            return result.stdout.strip() if capture else None

        subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL)
        assert run("ps", "-aq", capture=True) == ""
        started = False
        try:
            run("build")
            report["checks"].append("images_built_from_repository")
            started = True
            run(
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "--user",
                "0",
                "backend",
                "python",
                "-c",
                "import os; from pathlib import Path; p=Path('/qa-state'); assert not list(p.iterdir()); os.chown(p,10001,10001)",
            )
            run("up", "-d", "--wait", "--wait-timeout", "120")
            binding = run("port", "frontend", "80", capture=True)
            assert binding.startswith("127.0.0.1:")
            with httpx.Client(base_url="http://" + binding, timeout=40) as api:
                wait_ready(api)
                assert api.get("/").status_code == 200
                assert request(api, "GET", "/api/v1/capabilities")["ocr_ready"] is True
                report["checks"].append("startup_readiness_frontend_proxy")
                documents = []
                for kind in ("png", "jpeg"):
                    image = ROOT / "data/product/images/hoa_don_007.png"
                    content = image.read_bytes()
                    if kind == "jpeg":
                        with Image.open(image) as original:
                            encoded = io.BytesIO()
                            original.convert("RGB").save(
                                encoded, format="JPEG", quality=95
                            )
                            content = encoded.getvalue()
                    doc = request(
                        api,
                        "POST",
                        "/api/v1/documents",
                        202,
                        params={
                            "document_type": "hoa_don",
                            "data_origin": "synthetic",
                            "filename": "synthetic." + kind,
                        },
                        content=content,
                    )
                    path = "/api/v1/documents/" + doc["document_id"]
                    for _ in range(90):
                        doc = request(api, "GET", path)
                        if doc["run"]["status"] not in ("queued", "running"):
                            break
                        time.sleep(1)
                    assert doc["run"]["status"] == "succeeded"
                    assert doc["run"]["metadata"]["prediction_source"] == "model"
                    lock = json.loads(
                        (
                            ROOT
                            / "pipeline/src/document_pipeline/resources/tessdata-lock.json"
                        ).read_text()
                    )
                    metadata = doc["run"]["metadata"]
                    assert metadata["model_revision"] == lock["revision"]
                    assert metadata["model_sha256"] == lock["models"]
                    assert doc["run"]["spans"]
                    assert doc["input_sha256"] == hashlib.sha256(content).hexdigest()
                    run_id = doc["run"]["run_id"]

                    def save(fields, path=path, run_id=run_id):
                        current = request(api, "GET", path)
                        return request(
                            api,
                            "PUT",
                            path + "/review",
                            json={
                                "run_id": run_id,
                                "expected_revision": current["review"]["revision"],
                                "expected_status": "draft",
                                "fields": {
                                    k: {"is_reviewed": True, "reviewed_value": v}
                                    for k, v in fields.items()
                                },
                            },
                        )

                    cleared = save({"seller_name": None})
                    assert (
                        request(api, "GET", path)["review"]["effective_data"][
                            "seller_name"
                        ]
                        is None
                    )
                    request(
                        api,
                        "POST",
                        path + "/confirm",
                        422,
                        json={
                            "run_id": run_id,
                            "expected_revision": cleared["review"]["revision"],
                        },
                    )
                    visible = {
                        "invoice_number": "0041007",
                        "invoice_date": "2026-10-08",
                        "seller_name": "Công ty Giả Lập 107",
                        "total_amount": 1000000,
                        "currency": "VND",
                    }
                    saved = save(visible)
                    params = {"run_id": run_id, "revision": saved["review"]["revision"]}
                    request(api, "GET", path + "/export", 409, params=params)
                    request(
                        api,
                        "POST",
                        path + "/confirm",
                        json={
                            "run_id": run_id,
                            "expected_revision": params["revision"],
                        },
                    )
                    assert (
                        request(api, "GET", path + "/export", params=params)["data"]
                        == visible
                    )
                    documents.append(
                        {
                            "path": path,
                            "params": params,
                            "detail": request(api, "GET", path),
                            "preview_sha256": hashlib.sha256(
                                api.get(path + "/image").content
                            ).hexdigest(),
                            "history": request(api, "GET", path + "/history"),
                            "data": visible,
                        }
                    )
                report["checks"].append("native_png_jpeg_null_confirm_export")
                report["documents"] = [
                    {
                        "document_id": doc["detail"]["document_id"],
                        **doc["params"],
                        "input_sha256": doc["detail"]["input_sha256"],
                        "preview_sha256": doc["preview_sha256"],
                    }
                    for doc in documents
                ]
                run("restart")
                api.base_url = "http://" + run("port", "frontend", "80", capture=True)
                wait_ready(api)

                def verify():
                    for doc in documents:
                        assert request(api, "GET", doc["path"]) == doc["detail"]
                        assert (
                            request(api, "GET", doc["path"] + "/history")
                            == doc["history"]
                        )
                        assert (
                            hashlib.sha256(
                                api.get(doc["path"] + "/image").content
                            ).hexdigest()
                            == doc["preview_sha256"]
                        )
                    for doc in documents:
                        assert (
                            request(
                                api,
                                "GET",
                                doc["path"] + "/export",
                                params=doc["params"],
                            )["data"]
                            == doc["data"]
                        )

                verify()
                report["checks"].append("restart_same_volume_persistence")
                run("stop", "backend")
                probe = run(
                    "run",
                    "--rm",
                    "--no-deps",
                    "-T",
                    "backend",
                    "python",
                    "/qa/docker_volume_probe.py",
                    capture=True,
                )
                report["offline_probe"] = json.loads(probe)
                # Publish a restored copy only in the separate QA-state volume.
                text = config.read_text()
                config.write_text(
                    text.replace(
                        "DOCINTEL_AUTH_MODE: local",
                        "DOCINTEL_AUTH_MODE: local\n      DOCINTEL_RUNTIME_DIR: /qa-state/restored",
                    )
                )
                run("up", "-d", "--wait", "--wait-timeout", "120")
                run("restart", "frontend")
                api.base_url = "http://" + run("port", "frontend", "80", capture=True)
                wait_ready(api)
                # Export requests create events. Compare restored data/run/revision,
                # while the offline probe checks every stored history row exactly.
                for doc in documents:
                    assert request(api, "GET", doc["path"]) == doc["detail"]
                    assert (
                        request(
                            api, "GET", doc["path"] + "/export", params=doc["params"]
                        )["data"]
                        == doc["data"]
                    )
                report["checks"].append("restored_runtime_confirmed_export")
                report["native_metadata"] = documents[0]["detail"]["run"]["metadata"]
                report["status"] = "passed"
        finally:
            try:
                if started:
                    run("down", "--volumes", "--rmi", "local")
                    assert run("ps", "-aq", capture=True) == ""
                    volumes = subprocess.check_output(
                        [
                            "docker",
                            "volume",
                            "ls",
                            "-q",
                            "--filter",
                            "label=com.docker.compose.project=" + project,
                        ],
                        text=True,
                    ).strip()
                    assert not volumes
                    report["cleanup"] = "project containers and volumes removed"
            except BaseException:
                report["status"] = "failed"
                report["cleanup"] = "failed; inspect project-scoped resources"
                raise
            finally:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("x", encoding="utf-8") as stream:
                    json.dump(report, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
