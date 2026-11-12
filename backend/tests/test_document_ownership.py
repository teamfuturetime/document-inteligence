import pytest
from test_product import image_bytes
from test_product import product as product

from docintel.domain.documents import ReviewRequest, RevisionRequest
from docintel.repositories.identity import IdentityRepository
from docintel.services.documents import ProductError


@pytest.fixture
def tenants(product):
    api, settings = product
    service = api.app.state.documents
    identities = IdentityRepository(service.repository)
    alpha = service.for_owner(identities.create_user("alpha", "disabled-test-hash"))
    beta = service.for_owner(identities.create_user("beta", "disabled-test-hash"))
    return service, alpha, beta


def upload_as(service, key="same-key"):
    return service.upload(image_bytes(), "hoa_don", "synthetic", "synthetic.png", key)


def test_insights_counts_only_current_owners_documents_and_runs(tenants):
    root, alpha, beta = tenants
    a = upload_as(alpha)
    upload_as(beta)
    assert root.process_next()
    alpha.confirm(a.document_id, RevisionRequest(run_id=a.run.run_id, expected_revision=1))
    assert alpha.insights().documents == 1
    assert alpha.insights().completed_runs == 1
    assert alpha.insights().confirmed_documents == 1
    assert beta.insights().documents == 1
    assert beta.insights().completed_runs == 0
    assert beta.insights().confirmed_documents == 0
    assert root.insights().documents == 0


@pytest.mark.parametrize("operation", ["history", "image_path"])
def test_history_and_source_preview_do_not_leak_by_known_document_id(tenants, operation):
    root, alpha, beta = tenants
    a = upload_as(alpha)
    with pytest.raises(ProductError) as denied:
        getattr(beta, operation)(a.document_id)
    assert denied.value.status == 404
    assert alpha.history(a.document_id).events
    assert alpha.image_path(a.document_id).is_file()


def test_reprocess_checks_owner_before_provider_and_preserves_foreign_run(tenants, monkeypatch):
    root, alpha, beta = tenants
    a = upload_as(alpha)

    def must_not_probe():
        raise AssertionError("Foreign request reached provider")

    monkeypatch.setattr(beta, "ensure_ready", must_not_probe)
    with pytest.raises(ProductError) as denied:
        beta.reprocess(a.document_id, a.run.run_id)
    assert denied.value.status == 404
    assert alpha.detail(a.document_id).run.run_id == a.run.run_id


@pytest.mark.parametrize("operation", ["save_review", "confirm", "export"])
def test_revision_writes_and_exports_require_owner_inside_transaction(tenants, operation):
    root, alpha, beta = tenants
    a = upload_as(alpha)
    assert root.process_next()
    values = {"run_id": a.run.run_id, "expected_revision": 1}
    request = (
        ReviewRequest(**values, fields={})
        if operation == "save_review"
        else RevisionRequest(**values)
    )
    with pytest.raises(ProductError) as denied:
        getattr(beta, operation)(a.document_id, request)
    assert denied.value.status == 404
    assert alpha.detail(a.document_id).review.review_status == "draft"


def test_list_detail_and_pagination_never_cross_owner_boundary(tenants):
    root, alpha, beta = tenants
    a, b = upload_as(alpha), upload_as(beta)
    assert [item.document_id for item in alpha.list_documents(20, 0).items] == [a.document_id]
    assert alpha.list_documents(20, 1).items == []
    assert beta.list_documents(20, 0, "hoa_don", "queued").total == 1
    assert root.list_documents(20, 0).total == 0
    with pytest.raises(ProductError) as denied:
        beta.detail(a.document_id)
    assert denied.value.status == 404
    assert beta.detail(b.document_id).document_id == b.document_id


def test_idempotency_keys_are_isolated_per_owner_and_binding_is_not_shared(tenants):
    root, alpha, beta = tenants
    a, b = upload_as(alpha), upload_as(beta)
    assert a.document_id != b.document_id
    assert upload_as(alpha).document_id == a.document_id
    assert upload_as(beta).document_id == b.document_id
    assert root.owner_id == "local"
    assert alpha.owner_id != beta.owner_id
    with root.repository.transaction() as connection:
        assert {row[0] for row in connection.execute("SELECT owner_id FROM documents")} == {
            alpha.owner_id,
            beta.owner_id,
        }
