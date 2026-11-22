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


def stable_export(artifact):
    """Only download time may vary; compare persisted identity, data and provenance."""
    return {key: value for key, value in artifact.items() if key != "exported_at"}


def json_digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def wait_document(api, path):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        document = request(api, "GET", path)
        if document["run"]["status"] not in ("queued", "running"):
            assert document["run"]["status"] == "succeeded"
            return document
        time.sleep(1)
    raise RuntimeError("Native document processing timeout")


def resource_inventory(project):
    result = {}
    for resource, arguments in {
        "containers": ["ps", "-aq"],
        "volumes": ["volume", "ls", "-q"],
        "networks": ["network", "ls", "-q"],
    }.items():
        result[resource] = subprocess.check_output(
            [
                "docker",
                *arguments,
                "--filter",
                "label=com.docker.compose.project=" + project,
            ],
            text=True,
            timeout=20,
        ).split()
    result["images"] = subprocess.check_output(
        ["docker", "image", "ls", "-q", "--filter", "reference=" + project + "-*"],
        text=True,
        timeout=20,
    ).split()
    return result


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
        "report_version": 2,
        "project": project,
        "status": "failed",
        "checked_at": datetime.now(UTC).isoformat(),
        "checks": [],
        "head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        ).strip(),
        "base_main_sha": subprocess.check_output(
            ["git", "rev-parse", "origin/main"],
            cwd=ROOT,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
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
                "scripts/backup_runtime.py",
                "scripts/manage_auth.py",
                "backend/src/docintel/storage/backup.py",
                "backend/src/docintel/doctor.py",
                "backend/uv.lock",
                "frontend/package-lock.json",
                "pipeline/src/document_pipeline/resources/tessdata-lock.json",
            )
        },
    }
    report["git_head_at_execution"] = report["head"]
    report["tracked_tree_dirty_at_execution"] = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=ROOT,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        ).strip()
    )
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
        report["inventory_before"] = resource_inventory(project)
        assert not any(report["inventory_before"].values())
        started = True  # Cleanup also covers a partially completed image build.
        try:
            run("build")
            report["checks"].append("images_built_from_repository")
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
            report["inventory_running"] = resource_inventory(project)
            report["container_runtime"] = json.loads(
                run(
                    "exec",
                    "-T",
                    "backend",
                    "python",
                    "-c",
                    "import os,json,subprocess,hashlib; from pathlib import Path; "
                    "assert os.getuid()==10001; "
                    "print(json.dumps({'uid':os.getuid(),'tesseract':subprocess.check_output("
                    "['tesseract','--version'],text=True).splitlines()[0],"
                    "'models':{p.stem:hashlib.sha256(p.read_bytes()).hexdigest() "
                    "for p in Path('/opt/docintel-models').glob('*.traineddata')}}))",
                    capture=True,
                )
            )
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
                    doc = wait_document(api, path)
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
                    exported = request(api, "GET", path + "/export", params=params)
                    assert exported["data"] == visible
                    old_run = None
                    if kind == "png":
                        # Keep a genuine confirmed old run alongside a reprocessed latest run.
                        old_run = {
                            "params": params,
                            "detail": request(api, "GET", path),
                            "export": stable_export(exported),
                        }
                        request(
                            api,
                            "POST",
                            path + "/runs",
                            202,
                            json={"expected_run_id": run_id},
                        )
                        doc = wait_document(api, path)
                        run_id = doc["run"]["run_id"]
                        saved = request(
                            api,
                            "PUT",
                            path + "/review",
                            json={
                                "run_id": run_id,
                                "expected_revision": 1,
                                "expected_status": "draft",
                                "fields": {
                                    k: {"is_reviewed": True, "reviewed_value": v}
                                    for k, v in visible.items()
                                },
                            },
                        )
                        params = {
                            "run_id": run_id,
                            "revision": saved["review"]["revision"],
                        }
                        request(
                            api,
                            "POST",
                            path + "/confirm",
                            json={
                                "run_id": run_id,
                                "expected_revision": params["revision"],
                            },
                        )
                        exported = request(api, "GET", path + "/export", params=params)
                        assert exported["data"] == visible
                        old_run["detail"] = request(
                            api,
                            "GET",
                            path,
                            params={"run_id": old_run["params"]["run_id"]},
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
                            "export": stable_export(exported),
                            "old_run": old_run,
                        }
                    )
                report["checks"].append("native_png_jpeg_null_confirm_export")
                # Keep a current reviewed-null draft across every restart and restore.
                null_created = request(
                    api,
                    "POST",
                    "/api/v1/documents",
                    202,
                    params={"document_type": "hoa_don", "data_origin": "synthetic"},
                    content=image.read_bytes(),
                )
                null_path = "/api/v1/documents/" + null_created["document_id"]
                null_detail = wait_document(api, null_path)
                null_run = null_detail["run"]["run_id"]
                null_detail = request(
                    api,
                    "PUT",
                    null_path + "/review",
                    json={
                        "run_id": null_run,
                        "expected_revision": 1,
                        "fields": {
                            "seller_name": {"is_reviewed": True, "reviewed_value": None}
                        },
                    },
                )
                assert null_detail["review"]["effective_data"]["seller_name"] is None
                null_history = request(api, "GET", null_path + "/history")
                report["documents"] = [
                    {
                        "document_id": doc["detail"]["document_id"],
                        **doc["params"],
                        "input_sha256": doc["detail"]["input_sha256"],
                        "preview_sha256": doc["preview_sha256"],
                        "export_sha256_without_download_time": json_digest(
                            doc["export"]
                        ),
                        "old_run_id": doc["old_run"]["params"]["run_id"]
                        if doc["old_run"]
                        else None,
                    }
                    for doc in documents
                ]
                report["reviewed_null"] = {
                    "document_id": null_detail["document_id"],
                    "run_id": null_run,
                    "revision": 2,
                }
                run("restart")
                api.base_url = "http://" + run("port", "frontend", "80", capture=True)
                wait_ready(api)

                def verify():
                    assert request(api, "GET", null_path) == null_detail
                    assert request(api, "GET", null_path + "/history") == null_history
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
                        exported = request(
                            api, "GET", doc["path"] + "/export", params=doc["params"]
                        )
                        assert stable_export(exported) == doc["export"]
                        if doc["old_run"]:
                            old = doc["old_run"]
                            assert (
                                request(
                                    api,
                                    "GET",
                                    doc["path"],
                                    params={"run_id": old["params"]["run_id"]},
                                )
                                == old["detail"]
                            )
                            # Old runs are readable but mutations/downloads require latest-run CAS.
                            request(
                                api,
                                "GET",
                                doc["path"] + "/export",
                                409,
                                params=old["params"],
                            )

                verify()
                # Freeze the exact history that will enter the offline snapshot;
                # downloads above append legitimate export events.
                for doc in documents:
                    doc["history"] = request(api, "GET", doc["path"] + "/history")
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
                verify()
                report["checks"].append("restored_runtime_confirmed_export")
                # A separate restored copy was explicitly adopted before its own
                # snapshot. Never turn local legacy documents into first-login data.
                run("stop", "backend")
                text = config.read_text()
                config.write_text(
                    text.replace(
                        "DOCINTEL_AUTH_MODE: local",
                        "DOCINTEL_AUTH_MODE: session\n      DOCINTEL_SESSION_COOKIE_SECURE: 'false'",
                    ).replace("/qa-state/restored", "/qa-state/restored-session")
                )
                run("up", "-d", "--wait", "--wait-timeout", "120")
                run("restart", "frontend")
                api.base_url = "http://" + run("port", "frontend", "80", capture=True)
                wait_ready(api)
                request(api, "GET", documents[0]["path"], 401)
                credentials = json.loads(
                    run(
                        "exec",
                        "-T",
                        "backend",
                        "python",
                        "-c",
                        "from pathlib import Path; print(Path('/qa-state/http-auth.json').read_text())",
                        capture=True,
                    )
                )
                origin = {
                    "Origin": "http://127.0.0.1:5173",
                    "X-Requested-With": "docintel",
                }
                session = request(
                    api,
                    "POST",
                    "/api/v1/auth/login",
                    json={"username": "dockerqa", "password": credentials["dockerqa"]},
                    headers=origin,
                )
                api.headers.update(
                    {"Origin": origin["Origin"], "X-CSRF-Token": session["csrf_token"]}
                )
                verify()
                # The persisted session itself must survive a restart, not just a fresh login.
                session_histories = [
                    request(api, "GET", doc["path"] + "/history") for doc in documents
                ]
                run("restart")
                api.base_url = "http://" + run("port", "frontend", "80", capture=True)
                wait_ready(api)
                assert (
                    request(api, "GET", "/api/v1/auth/session")["user"]
                    == session["user"]
                )
                assert request(api, "GET", null_path) == null_detail
                for doc, history in zip(documents, session_histories, strict=True):
                    assert request(api, "GET", doc["path"]) == doc["detail"]
                    assert request(api, "GET", doc["path"] + "/history") == history
                foreign = request(
                    api,
                    "POST",
                    "/api/v1/auth/login",
                    json={
                        "username": "foreignqa",
                        "password": credentials["foreignqa"],
                    },
                    headers=origin,
                )
                api.headers["X-CSRF-Token"] = foreign["csrf_token"]
                for doc in documents:
                    for suffix in ("", "/history", "/image"):
                        request(api, "GET", doc["path"] + suffix, 404)
                    request(
                        api, "GET", doc["path"] + "/export", 404, params=doc["params"]
                    )
                    request(
                        api,
                        "PUT",
                        doc["path"] + "/review",
                        404,
                        json={
                            "run_id": doc["params"]["run_id"],
                            "expected_revision": doc["params"]["revision"],
                            "fields": {},
                        },
                    )
                del credentials
                report["checks"].append(
                    "restored_session_http_owner_isolation_and_restart"
                )
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
                    report["inventory_after"] = resource_inventory(project)
                    assert not any(report["inventory_after"].values())
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
