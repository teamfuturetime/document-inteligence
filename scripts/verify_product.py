"""Native OCR + HTTP workflow check. Missing engines/models fail, never skip."""

import argparse
import hashlib
import io
import json
import tempfile
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import connect

from docintel.api.app import create_app
from docintel.config import ROOT, Settings
from docintel.security import hash_password, new_token
from fastapi.testclient import TestClient
from PIL import Image


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


def confirm_pdf_with_failed_delivery(api, runtime, path, run_id, revision, visible):
    """Inject only delivery failure and observe the commit from a fresh SQLite connection."""
    attempts = []

    class FailingSender:
        async def send(self, notice):
            with closing(connect(runtime / "documents.sqlite3")) as db:
                row = db.execute(
                    "SELECT review_status, fields_json FROM revisions WHERE run_id=? AND revision=?",
                    (notice.run_id, notice.revision),
                ).fetchone()
            attempts.append((notice.run_id, notice.revision, row))
            raise RuntimeError("synthetic delivery failure")

    body = {"run_id": run_id, "expected_revision": revision}
    original = api.app.state.confirmation_notifier
    api.app.state.confirmation_notifier = FailingSender()
    try:
        confirmed = check(api.post(path + "/confirm", json=body))
        assert confirmed["review"]["review_status"] == "confirmed"
        assert confirmed["review"]["revision"] == revision
        retried = check(api.post(path + "/confirm", json=body))
        assert retried["review"] == confirmed["review"]
    finally:
        api.app.state.confirmation_notifier = original
    # Assert outside the sender so the best-effort delivery handler cannot swallow failures.
    assert len(attempts) == 1
    noticed_run, noticed_revision, persisted = attempts[0]
    assert (noticed_run, noticed_revision) == (run_id, revision)
    assert persisted is not None and persisted[0] == "confirmed"
    assert {
        name: field["reviewed_value"]
        for name, field in json.loads(persisted[1]).items()
        if field["is_reviewed"]
    } == visible
    history = check(api.get(path + "/history"))
    assert [
        event["revision"]
        for event in history["events"]
        if event["run_id"] == run_id and event["action"] == "confirmed"
    ] == [revision]


def verify_pdf_reprocess_history(api, path, run, revision, source, original_bytes):
    run_id = run["run_id"]
    selected_run = {"run_id": run_id}
    old = check(api.get(path, params=selected_run))
    old_history = check(api.get(path + "/history"))
    queued = check(api.post(path + "/runs", json={"expected_run_id": run_id}), 202)
    assert queued["latest_run_id"] != run_id
    current = wait_for_run(api, queued)
    assert current["run"]["run_id"] == queued["latest_run_id"]
    assert current["run"]["metadata"]["prediction_source"] == "model"
    assert current["review"]["review_status"] == "draft"
    archived = check(api.get(path, params=selected_run))
    assert archived["is_latest_run"] is False
    assert archived["run"] == old["run"] == run
    assert archived["review"] == old["review"]
    stale = {**selected_run, "expected_revision": revision}
    for response in (
        api.put(path + "/review", json={**stale, "fields": {}}),
        api.post(path + "/confirm", json=stale),
        api.get(path + "/export", params={**selected_run, "revision": revision}),
    ):
        assert check(response, 409)["error"]["code"] == "STALE_RUN"
    history = check(api.get(path + "/history"))
    assert {entry["run_id"]: entry for entry in history["runs"]}[run_id] == run
    assert [event for event in history["events"] if event["run_id"] == run_id] == [
        event for event in old_history["events"] if event["run_id"] == run_id
    ]
    assert check(api.get(path, params=selected_run))["review"] == old["review"]
    assert source.read_bytes() == original_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "runtime/verification/product-native.json"
    )
    parser.add_argument("--auth-mode", choices=("local", "session"), default="local")
    args = parser.parse_args()
    settings = Settings(
        provider_mode="tesseract", auth_mode=args.auth_mode, notification_mode="log"
    )
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
            pdf = ROOT / "pipeline/tests/fixtures/pdf/hoa_don_007.pdf"
            pdf_document = wait_for_run(
                api,
                check(
                    api.post(
                        "/api/v1/documents",
                        params={
                            "document_type": "hoa_don",
                            "data_origin": "synthetic",
                            "filename": pdf.name,
                        },
                        content=pdf.read_bytes(),
                        headers={"Content-Type": "application/pdf"},
                    ),
                    202,
                ),
            )
            pdf_run = pdf_document["run"]
            pdf_metadata = pdf_run["metadata"]
            assert pdf_metadata["prediction_source"] == "model"
            assert (
                pdf_metadata["preprocessing"]["source_frame"]
                == "pdf_raster_pixels_top_left"
            )
            preview = api.get(pdf_document["image_url"])
            assert (
                preview.status_code == 200
                and preview.headers["content-type"] == "image/png"
            )
            with Image.open(io.BytesIO(preview.content)) as raster:
                width, height = raster.size
            assert (width, height) == (
                pdf_document["image_width"],
                pdf_document["image_height"],
            )
            frame = pdf_metadata["preprocessing"]
            assert (frame["width"], frame["height"]) == (width, height)
            assert pdf_run["spans"]
            for span in pdf_run["spans"]:
                x1, y1, x2, y2 = span["box"]
                assert 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height
            pdf_path = "/api/v1/documents/" + pdf_document["document_id"]
            pdf_bytes = pdf.read_bytes()
            pdf_source = (
                settings.runtime_dir
                / "documents"
                / (pdf_document["document_id"] + ".source")
            )
            assert pdf_source.read_bytes() == pdf_bytes
            assert (
                pdf_document["input_sha256"]
                == pdf_metadata["input_sha256"]
                == hashlib.sha256(pdf_bytes).hexdigest()
            )
            checks.append("pdf_raw_source_and_checksum")
            pdf_cleared = check(
                api.put(
                    pdf_path + "/review",
                    json={
                        "run_id": pdf_run["run_id"],
                        "expected_revision": pdf_document["review"]["revision"],
                        "expected_status": "draft",
                        "fields": {
                            "seller_name": {"is_reviewed": True, "reviewed_value": None}
                        },
                    },
                )
            )
            assert (
                check(api.get(pdf_path))["review"]["effective_data"]["seller_name"]
                is None
            )
            check(
                api.put(
                    pdf_path + "/review",
                    json={
                        "run_id": pdf_run["run_id"],
                        "expected_revision": 1,
                        "fields": {},
                    },
                ),
                409,
            )
            check(
                api.post(
                    pdf_path + "/confirm",
                    json={
                        "run_id": pdf_run["run_id"],
                        "expected_revision": pdf_cleared["review"]["revision"],
                    },
                ),
                422,
            )
            pdf_saved = check(
                api.put(
                    pdf_path + "/review",
                    json={
                        "run_id": pdf_run["run_id"],
                        "expected_revision": pdf_cleared["review"]["revision"],
                        "expected_status": "draft",
                        "fields": {
                            key: {"is_reviewed": True, "reviewed_value": value}
                            for key, value in visible.items()
                        },
                    },
                )
            )
            pdf_revision = pdf_saved["review"]["revision"]
            pdf_export_params = {"run_id": pdf_run["run_id"], "revision": pdf_revision}
            assert (
                check(api.get(pdf_path + "/export", params=pdf_export_params), 409)[
                    "error"
                ]["code"]
                == "NOT_CONFIRMED"
            )
            if args.auth_mode == "session":
                confirm_pdf_with_failed_delivery(
                    api,
                    settings.runtime_dir,
                    pdf_path,
                    pdf_run["run_id"],
                    pdf_revision,
                    visible,
                )
                checks.append("pdf_notification_failure_after_sqlite_commit_and_retry")
            else:
                check(
                    api.post(
                        pdf_path + "/confirm",
                        json={
                            "run_id": pdf_run["run_id"],
                            "expected_revision": pdf_revision,
                        },
                    )
                )
            pdf_artifact = check(
                api.get(pdf_path + "/export", params=pdf_export_params)
            )
            assert (
                pdf_artifact["data"] == visible
                and pdf_artifact["revision"] == pdf_revision
            )
            check(
                api.put(
                    pdf_path + "/review",
                    json={
                        "run_id": pdf_run["run_id"],
                        "expected_revision": pdf_revision,
                        "expected_status": "draft",
                        "fields": {},
                    },
                ),
                409,
            )
            assert check(api.get(pdf_path))["run"] == pdf_run
            checks.extend(
                [
                    "pdf_native_raster_and_evidence",
                    "pdf_review_confirm_export",
                    "pdf_explicit_null_and_revision_cas",
                    "pdf_confirmed_status_cas",
                ]
            )
            if args.auth_mode == "session":
                authenticate(api, "verifybeta")
                assert check(api.get("/api/v1/documents"))["total"] == 0
                assert check(api.get("/api/v1/insights"))["documents"] == 0
                for suffix in (
                    "",
                    "/image",
                    "/history",
                    f"/export?run_id={pdf_run['run_id']}&revision={pdf_revision}",
                ):
                    assert api.get(pdf_path + suffix).status_code == 404
                for method, suffix, body in (
                    (
                        "PUT",
                        "/review",
                        {
                            "run_id": pdf_run["run_id"],
                            "expected_revision": pdf_revision,
                            "expected_status": "confirmed",
                            "fields": {},
                        },
                    ),
                    (
                        "POST",
                        "/confirm",
                        {
                            "run_id": pdf_run["run_id"],
                            "expected_revision": pdf_revision,
                        },
                    ),
                    ("POST", "/runs", {"expected_run_id": pdf_run["run_id"]}),
                ):
                    assert (
                        api.request(method, pdf_path + suffix, json=body).status_code
                        == 404
                    )
                checks.append("pdf_session_owner_resource_isolation")
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
                assert check(restarted.get("/api/v1/documents"))["total"] == 3
            assert (
                check(restarted.get(path, params={"run_id": original_run}))["review"][
                    "effective_data"
                ]
                == visible
            )
            checks.append("sqlite_persistence_after_restart")
            assert check(restarted.get(pdf_path))["run"] == pdf_run
            assert restarted.get(pdf_document["image_url"]).content == preview.content
            assert (
                check(
                    restarted.get(
                        pdf_path + "/export",
                        params={"run_id": pdf_run["run_id"], "revision": pdf_revision},
                    )
                )["data"]
                == visible
            )
            checks.append("pdf_confirmed_persistence_after_restart")
            if args.auth_mode == "session":
                verify_pdf_reprocess_history(
                    restarted, pdf_path, pdf_run, pdf_revision, pdf_source, pdf_bytes
                )
                checks.append("pdf_native_reprocess_preserves_read_only_history")
    report = {
        "report_type": "native_workflow_check",
        "status": "passed",
        "auth_mode": args.auth_mode,
        "checked_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "native_run_metadata": document["run"]["metadata"],
        "pdf_native_run_metadata": pdf_metadata,
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
