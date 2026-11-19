"""Native OCR + HTTP workflow check. Missing engines/models fail, never skip."""

import argparse
import json
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from docintel.api.app import create_app
from docintel.config import ROOT, Settings
from docintel.security import hash_password, new_token
from fastapi.testclient import TestClient


def check(response, expected=200):
    if response.status_code != expected:
        raise AssertionError(f"HTTP {response.status_code}: {response.text[:400]}")
    return response.json()


def wait_for_run(api, document):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        document = check(api.get("/api/v1/documents/" + document["document_id"]))
        if document["run"]["status"] not in ("queued", "running"):
            if document["run"]["status"] != "succeeded":
                raise AssertionError(document["run"]["error_code"])
            return document
        time.sleep(0.1)
    raise AssertionError("Persisted run did not finish within deadline")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "runtime/verification/product-native.json"
    )
    parser.add_argument("--auth-mode", choices=("local", "session"), default="local")
    args = parser.parse_args()
    settings = Settings(provider_mode="tesseract", auth_mode=args.auth_mode)
    password = new_token()
    origin = settings.cors_origins[0]

    def authenticate(api, username="verifyalpha"):
        state = check(
            api.post(
                "/api/v1/auth/login",
                json={"username": username, "password": password},
                headers={"Origin": origin, "X-Requested-With": "docintel"},
            )
        )
        api.headers["X-CSRF-Token"] = state["csrf_token"]

    checks = []
    with tempfile.TemporaryDirectory(prefix="docintel-verify-") as directory:
        settings.runtime_dir = Path(directory)
        with TestClient(create_app(settings), base_url="https://testserver") as api:
            if args.auth_mode == "session":
                assert api.get("/api/v1/documents").status_code == 401
                identities = api.app.state.auth.identities
                for username in ("verifyalpha", "verifybeta"):
                    identities.create_user(username, hash_password(password))
                authenticate(api)
            assert check(api.get("/api/v1/capabilities"))["ocr_ready"] is True
            image = ROOT / "data/product/images/hoa_don_007.png"
            document = check(
                api.post(
                    "/api/v1/documents",
                    params={
                        "document_type": "hoa_don",
                        "data_origin": "synthetic",
                        "filename": image.name,
                    },
                    content=image.read_bytes(),
                    headers={"Idempotency-Key": "native-invoice"},
                ),
                202,
            )
            repeated = check(
                api.post(
                    "/api/v1/documents",
                    params={
                        "document_type": "hoa_don",
                        "data_origin": "synthetic",
                        "filename": image.name,
                    },
                    content=image.read_bytes(),
                    headers={"Idempotency-Key": "native-invoice"},
                ),
                202,
            )
            assert repeated["document_id"] == document["document_id"]
            document = wait_for_run(api, document)
            assert document["run"]["metadata"]["prediction_source"] == "model"
            assert document["run"]["spans"]
            checks.extend(
                [
                    "real_vie_eng_ocr",
                    "persisted_async_run",
                    "upload_idempotency",
                    "source_evidence",
                ]
            )
            path = "/api/v1/documents/" + document["document_id"]
            request = {"run_id": document["run"]["run_id"], "expected_revision": 1}
            check(
                api.get(
                    path + "/export",
                    params={"run_id": request["run_id"], "revision": 1},
                ),
                409,
            )
            # Source-visible values of this self-designed development sample. This
            # scripted review is NOT used as a prediction or model-quality metric.
            check(api.post(path + "/confirm", json={**request, "approved": True}), 422)
            visible = {
                "invoice_number": "0041007",
                "invoice_date": "2026-10-08",
                "seller_name": "Công ty Giả Lập 107",
                "total_amount": 1000000,
                "currency": "VND",
            }
            saved = check(
                api.put(
                    path + "/review",
                    json={
                        **request,
                        "fields": {
                            key: {"is_reviewed": True, "reviewed_value": value}
                            for key, value in visible.items()
                        },
                    },
                )
            )
            check(api.put(path + "/review", json={**request, "fields": {}}), 409)
            cleared = check(
                api.put(
                    path + "/review",
                    json={
                        "run_id": request["run_id"],
                        "expected_revision": saved["review"]["revision"],
                        "fields": {
                            "seller_name": {"is_reviewed": True, "reviewed_value": None}
                        },
                    },
                )
            )
            assert (
                check(api.get(path))["review"]["effective_data"]["seller_name"] is None
            )
            check(
                api.post(
                    path + "/confirm",
                    json={
                        "run_id": request["run_id"],
                        "expected_revision": cleared["review"]["revision"],
                    },
                ),
                422,
            )
            restored = check(
                api.put(
                    path + "/review",
                    json={
                        "run_id": request["run_id"],
                        "expected_revision": cleared["review"]["revision"],
                        "fields": {
                            "seller_name": {
                                "is_reviewed": True,
                                "reviewed_value": visible["seller_name"],
                            }
                        },
                    },
                )
            )
            revision = restored["review"]["revision"]
            check(
                api.post(
                    path + "/confirm",
                    json={"run_id": request["run_id"], "expected_revision": revision},
                )
            )
            artifact = check(
                api.get(
                    path + "/export",
                    params={"run_id": request["run_id"], "revision": revision},
                )
            )
            assert artifact["data"] == visible
            assert artifact["revision"] == revision
            checks.extend(
                [
                    "draft_save_reload",
                    "explicit_review_null",
                    "two_client_conflict_409",
                    "invalid_confirm_rejected",
                    "backend_confirmed_export",
                    "no_client_approval_bypass",
                ]
            )
            original_run = request["run_id"]
            rerun = check(
                api.post(path + "/runs", json={"expected_run_id": original_run}), 202
            )
            check(
                api.get(
                    path + "/export",
                    params={"run_id": original_run, "revision": revision},
                ),
                409,
            )
            wait_for_run(api, rerun)
            old = check(api.get(path, params={"run_id": original_run}))
            assert old["review"]["effective_data"] == visible
            assert old["review"]["review_status"] == "confirmed"
            checks.extend(
                ["reprocess_keeps_review_history", "stale_run_export_rejected"]
            )
            application_image = ROOT / "data/fixtures/images/fixture_001.png"
            application = check(
                api.post(
                    "/api/v1/documents",
                    params={
                        "document_type": "don_de_nghi",
                        "data_origin": "synthetic",
                        "filename": application_image.name,
                    },
                    content=application_image.read_bytes(),
                ),
                202,
            )
            application = wait_for_run(api, application)
            assert len(application["run"]["fields"]) == 7
            check(
                api.post(
                    "/api/v1/documents/" + application["document_id"] + "/confirm",
                    json={
                        "run_id": application["run"]["run_id"],
                        "expected_revision": application["review"]["revision"],
                    },
                )
            )
            checks.append("both_document_schemas_real_pipeline")
            if args.auth_mode == "session":
                authenticate(api, "verifybeta")
                assert check(api.get("/api/v1/documents"))["total"] == 0
                assert check(api.get("/api/v1/insights"))["documents"] == 0
                for suffix in (
                    "",
                    "/image",
                    "/history",
                    f"/export?run_id={original_run}&revision={revision}",
                ):
                    assert api.get(path + suffix).status_code == 404
                for method, suffix, body in (
                    (
                        "PUT",
                        "/review",
                        {
                            "run_id": original_run,
                            "expected_revision": revision,
                            "fields": {},
                        },
                    ),
                    (
                        "POST",
                        "/confirm",
                        {"run_id": original_run, "expected_revision": revision},
                    ),
                    ("POST", "/runs", {"expected_run_id": document["latest_run_id"]}),
                ):
                    assert (
                        api.request(method, path + suffix, json=body).status_code == 404
                    )
                other = check(
                    api.post(
                        "/api/v1/documents",
                        params={
                            "document_type": "hoa_don",
                            "data_origin": "synthetic",
                            "filename": image.name,
                        },
                        content=image.read_bytes(),
                        headers={"Idempotency-Key": "native-invoice"},
                    ),
                    202,
                )
                assert other["document_id"] != document["document_id"]
                wait_for_run(api, other)
                assert api.post("/api/v1/auth/logout").status_code == 204
                assert api.get("/api/v1/documents").status_code == 401
                checks.extend(
                    [
                        "session_login_csrf_logout",
                        "two_owner_resource_isolation",
                        "owner_idempotency_namespace",
                    ]
                )
        with TestClient(
            create_app(settings), base_url="https://testserver"
        ) as restarted:
            if args.auth_mode == "session":
                authenticate(restarted)
                assert check(restarted.get("/api/v1/documents"))["total"] == 2
            assert (
                check(restarted.get(path, params={"run_id": original_run}))["review"][
                    "effective_data"
                ]
                == visible
            )
            checks.append("sqlite_persistence_after_restart")
    report = {
        "report_type": "native_workflow_check",
        "status": "passed",
        "auth_mode": args.auth_mode,
        "checked_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "native_run_metadata": document["run"]["metadata"],
        "note": "Actual Tesseract inference and HTTP workflow; scripted review is not AI accuracy",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {"status": "passed", "checks": len(checks), "report": str(args.output)},
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
