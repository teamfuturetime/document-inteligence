import pytest
from test_product import image_bytes
from test_product import product as product

from docintel.repositories.identity import IdentityRepository


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
