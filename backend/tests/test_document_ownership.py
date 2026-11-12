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
