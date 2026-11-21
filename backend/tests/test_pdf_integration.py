"""PDF admission + real SQLite/session/backup; inference is an explicit workflow double."""

import hashlib

from fastapi.testclient import TestClient
from test_auth_api import ORIGIN, login
from test_auth_api import session_api as session_api

from docintel.api.app import create_app
from docintel.config import ROOT

PDF = ROOT / "pipeline/tests/fixtures/pdf/hoa_don_007.pdf"


def upload(api, key="pdf-owner-key"):
    return api.post(
        "/api/v1/documents",
        params={"document_type": "hoa_don", "data_origin": "synthetic", "filename": PDF.name},
        content=PDF.read_bytes(),
        headers={"Content-Type": "application/pdf", "Idempotency-Key": key},
    )


def authenticate(api, username="alpha"):
    state = login(api, username)
    api.headers.update({"Origin": ORIGIN, "X-CSRF-Token": state["csrf_token"]})


def processed(api):
    response = upload(api)
    assert response.status_code == 202, response.text
    document = response.json()
    assert api.app.state.documents.process_next()
    return api.get("/api/v1/documents/" + document["document_id"]).json()


def test_pdf_session_owner_checks_all_resources_and_idempotency_namespace(session_api):
    api, settings = session_api
    authenticate(api)
    document = processed(api)
    path = "/api/v1/documents/" + document["document_id"]
    original = api.get(path).json()
    preview = api.get(path + "/image").content
    assert preview.startswith(b"\x89PNG")
    assert document["input_sha256"] == hashlib.sha256(PDF.read_bytes()).hexdigest()
    replay = upload(api)
    assert replay.status_code == 202
    assert replay.json()["document_id"] == document["document_id"]
    authenticate(api, "beta")
    assert api.get("/api/v1/documents").json()["total"] == 0
    request = {"run_id": document["run"]["run_id"], "expected_revision": 1}
    for suffix in ("", "/image", "/history", f"/export?run_id={request['run_id']}&revision=1"):
        assert api.get(path + suffix).status_code == 404
    for method, suffix, body in (
        ("PUT", "/review", {**request, "expected_status": "draft", "fields": {}}),
        ("POST", "/confirm", request),
        ("POST", "/runs", {"expected_run_id": request["run_id"]}),
    ):
        assert api.request(method, path + suffix, json=body).status_code == 404
    own = upload(api)
    assert own.status_code == 202
    assert own.json()["document_id"] != document["document_id"]
    authenticate(api)
    assert api.get(path).json() == original
    assert api.get(path + "/image").content == preview
    assert (
        settings.runtime_dir / "documents" / (document["document_id"] + ".source")
    ).read_bytes() == PDF.read_bytes()


def test_pdf_null_status_cas_notification_failure_and_owned_restore(
    session_api, monkeypatch, tmp_path_factory
):
    api, settings = session_api
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import backup_runtime

    authenticate(api)
    document = processed(api)
    path = "/api/v1/documents/" + document["document_id"]
    run_id = document["run"]["run_id"]
    original_prediction = document["run"]
    cleared = api.put(
        path + "/review",
        json={
            "run_id": run_id,
            "expected_revision": 1,
            "expected_status": "draft",
            "fields": {"seller_name": {"is_reviewed": True, "reviewed_value": None}},
        },
    )
    assert cleared.status_code == 200
    assert api.get(path).json()["review"]["effective_data"]["seller_name"] is None
    assert (
        api.post(path + "/confirm", json={"run_id": run_id, "expected_revision": 2}).status_code
        == 422
    )
    assert (
        api.put(
            path + "/review", json={"run_id": run_id, "expected_revision": 1, "fields": {}}
        ).status_code
        == 409
    )
    saved = api.put(
        path + "/review",
        json={
            "run_id": run_id,
            "expected_revision": 2,
            "expected_status": "draft",
            "fields": {
                "seller_name": {"is_reviewed": True, "reviewed_value": "PDF reviewed seller"}
            },
        },
    )
    assert saved.status_code == 200
    revision = saved.json()["review"]["revision"]
    delivered = []
    owner_id = api.get("/api/v1/auth/session").json()["user"]["id"]

    class FailingSender:
        async def send(self, notice):
            # Observe through a new SQLite transaction, after business commit.
            detail = api.app.state.documents.for_owner(owner_id).detail(document["document_id"])
            assert detail.review.review_status == "confirmed"
            delivered.append(notice.event_id)
            raise RuntimeError("synthetic notification transport failure")

    settings.notification_mode = "log"
    api.app.state.confirmation_notifier = FailingSender()
    request = {"run_id": run_id, "expected_revision": revision}
    assert api.post(path + "/confirm", json=request).status_code == 200
    assert api.post(path + "/confirm", json=request).status_code == 200
    assert len(delivered) == 1
    # A late draft ACK/request must not reopen the now-confirmed revision.
    assert (
        api.put(
            path + "/review", json={**request, "expected_status": "draft", "fields": {}}
        ).status_code
        == 409
    )
    before = api.get(path).json()
    assert before["run"] == original_prediction
    params = {"run_id": run_id, "revision": revision}
    artifact = api.get(path + "/export", params=params).json()
    history = api.get(path + "/history").json()
    preview = api.get(path + "/image").content
    roundtrip = tmp_path_factory.mktemp("pdf-roundtrip")
    snapshot, restored = roundtrip / "backup", roundtrip / "restored"
    backup_runtime.backup(settings.runtime_dir, snapshot)
    backup_runtime.restore(snapshot, restored)
    with TestClient(
        create_app(settings.model_copy(update={"runtime_dir": restored}), start_worker=False),
        base_url="https://testserver",
    ) as recovered:
        authenticate(recovered)
        assert recovered.get(path).json() == before
        assert recovered.get(path + "/history").json() == history
        assert recovered.get(path + "/image").content == preview
        exported = recovered.get(path + "/export", params=params).json()
        assert {k: v for k, v in exported.items() if k != "exported_at"} == {
            k: v for k, v in artifact.items() if k != "exported_at"
        }
        assert (
            restored / "documents" / (document["document_id"] + ".source")
        ).read_bytes() == PDF.read_bytes()
        authenticate(recovered, "beta")
        assert recovered.get(path).status_code == 404
        assert recovered.get(path + "/export", params=params).status_code == 404


def test_pdf_auth_and_csrf_reject_before_admission(session_api):
    api, settings = session_api
    assert upload(api).status_code == 401
    login(api)
    assert upload(api).status_code == 403
    assert api.get("/api/v1/documents").json()["total"] == 0
    assert list((settings.runtime_dir / "documents").iterdir()) == []
