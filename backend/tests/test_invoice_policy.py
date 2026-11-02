"""VT-045 consumer/provider contracts: assert business outcomes, not status alone."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.schemas.invoice import MAX_SAFE_INTEGER
from app.schemas.validation import ValidationResult
from app.services.normalization import normalize_invoice
from app.services import validation


RAW = {
    "invoice_number": "0000123", "invoice_date": "03/04/2026",
    "seller_name": "Cửa hàng Mây Việt", "total_amount": "125.000 ₫", "currency": None,
}
EXPECTED = {
    "invoice_number": "0000123", "invoice_date": "2026-04-03",
    "seller_name": "Cửa hàng Mây Việt", "total_amount": 125000, "currency": "VND",
}


def write_policy(path: Path, ceiling: int) -> Path:
    path.write_text(json.dumps({"policy_version": "invoice-policy-1", "max_total_amount": ceiling}), encoding="utf-8")
    return path


def validate(path: Path, raw: dict | None = None):
    return validation.validate_invoice(normalize_invoice(RAW if raw is None else raw, source_locale="vi-VN"), policy_path=path)


def test_tc02_json_only_reload_changes_business_outcome(tmp_path, monkeypatch):
    # This also executes on the unmodified baseline: it MUST fail on business
    # outcome, not collection/import failure or an unknown keyword argument.
    path = write_policy(tmp_path / "policy.json", 200000)
    monkeypatch.setattr(validation, "DEFAULT_POLICY_PATH", path, raising=False)
    normalized = normalize_invoice(RAW, source_locale="vi-VN")
    assert validation.validate_invoice(normalized).normalized_values.model_dump() == EXPECTED
    write_policy(path, 100000)
    result = validation.validate_invoice(normalized)
    assert result.valid is False, "JSON-only policy change must reject 125000 above 100000"
    assert result.normalized_values.total_amount is None
    assert [(e.field, e.code) for e in result.errors] == [("total_amount", "business.amount_exceeds_policy")]


@pytest.mark.parametrize("amount,valid", [(0, True), (99999, True), (100000, True), (100001, False)])
def test_tc03_boundary_contract(tmp_path, amount, valid):
    path = write_policy(tmp_path / "policy.json", 100000)
    # Integer amounts carry no VND suffix: currency must be explicit evidence.
    raw = {**RAW, "total_amount": amount, "currency": "VND"}
    snapshot = deepcopy(raw)
    result = validate(path, raw)
    assert result.valid is valid
    assert result.normalized_values.total_amount == (amount if valid else None)
    assert [(e.field, e.code) for e in result.errors] == ([] if valid else [("total_amount", "business.amount_exceeds_policy")])
    assert raw == snapshot
    assert {k: v for k, v in result.normalized_values.model_dump().items() if k != "total_amount"} == {k: v for k, v in EXPECTED.items() if k != "total_amount"}


def test_tc01_default_preserves_safe_integer_contract():
    result = validation.validate_invoice(normalize_invoice({**EXPECTED, "total_amount": MAX_SAFE_INTEGER}))
    assert result.valid is True
    assert result.normalized_values.total_amount == MAX_SAFE_INTEGER
    assert set(result.model_dump()) == {"valid", "normalized_values", "errors", "warnings"}


@pytest.mark.parametrize("contents", [
    "{", "[]", '{}',
    '{"policy_version":"invoice-policy-1","max_total_amount":true}',
    '{"policy_version":"invoice-policy-1","max_total_amount":"100000"}',
    '{"policy_version":"invoice-policy-1","max_total_amount":1.5}',
    '{"policy_version":"invoice-policy-1","max_total_amount":-1}',
    '{"policy_version":"invoice-policy-1","max_total_amount":9007199254740992}',
    '{"policy_version":"invoice-policy-2","max_total_amount":1}',
    '{"policy_version":"invoice-policy-1","max_total_amount":1,"extra":0}',
    '{"policy_version":"invoice-policy-1","max_total_amount":1,"max_total_amount":2}',
])
def test_tc04_invalid_configuration_never_defaults(tmp_path, contents):
    from app.services.invoice_policy import InvoicePolicyError
    path = tmp_path / "policy.json"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(InvoicePolicyError, match="Invoice policy is unavailable or invalid"):
        validate(path)


def test_tc05_read_failure_is_not_swallowed(tmp_path):
    from app.services.invoice_policy import InvoicePolicyError
    with pytest.raises(InvoicePolicyError, match="Invoice policy is unavailable or invalid"):
        validate(tmp_path / "missing-private-policy.json")


def test_tc05_permission_failure_is_not_swallowed(tmp_path, monkeypatch):
    from app.services.invoice_policy import InvoicePolicyError
    path = write_policy(tmp_path / "policy.json", 100000)
    original = Path.read_text
    def denied(self, *args, **kwargs):
        if self == path:
            raise PermissionError("private configuration details")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(InvoicePolicyError, match="^Invoice policy is unavailable or invalid$"):
        validate(path)


@pytest.mark.parametrize("field,value,code", [
    ("currency", "USD", "business.unsupported_currency"),
    ("total_amount", "125,000", "normalization.ambiguous_amount"),
    ("total_amount", -1, "business.out_of_range"),
    ("total_amount", MAX_SAFE_INTEGER + 1, "business.out_of_range"),
])
def test_tc06_existing_errors_are_not_replaced(tmp_path, field, value, code):
    path = write_policy(tmp_path / "policy.json", MAX_SAFE_INTEGER)
    result = validate(path, {**EXPECTED, field: value})
    assert result.valid is False
    assert [(e.field, e.code) for e in result.errors] == [(field, code)]
    assert result.normalized_values.model_dump()[field] is None


def test_tc07_result_round_trip_and_detached_input(tmp_path):
    path = write_policy(tmp_path / "policy.json", 100000)
    original = deepcopy(RAW)
    normalized = normalize_invoice(RAW, source_locale="vi-VN")
    snapshot = deepcopy(normalized)
    result = validation.validate_invoice(normalized, policy_path=path)
    assert result.valid is False
    assert ValidationResult.model_validate_json(result.model_dump_json()) == result
    assert RAW == original
    assert normalized == snapshot
    result.normalized_values.seller_name = "Changed seller"
    assert validate(path).normalized_values.seller_name == EXPECTED["seller_name"]


def test_tc08_policy_snapshot_is_immutable(tmp_path):
    from pydantic import ValidationError
    from app.services.invoice_policy import load_invoice_policy
    path = write_policy(tmp_path / "policy.json", 0)
    snapshot = load_invoice_policy(path)
    with pytest.raises(ValidationError):
        snapshot.max_total_amount = 1
    write_policy(path, MAX_SAFE_INTEGER)
    assert snapshot.max_total_amount == 0
    assert load_invoice_policy(path).max_total_amount == MAX_SAFE_INTEGER


def test_tc09_http_contract_business_rejection_and_failure(tmp_path):
    import importlib.util
    from starlette.testclient import TestClient
    harness_path = Path(__file__).resolve().parents[2] / "homework/VT-045/harness.py"
    spec = importlib.util.spec_from_file_location("vt045_harness", harness_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = write_policy(tmp_path / "policy.json", 100000)
    with TestClient(module.create_app(path)) as client:
        response = client.post("/validate", json=RAW)
        assert response.status_code == 200
        result = ValidationResult.model_validate(response.json())
        assert result.valid is False
        assert result.normalized_values.total_amount is None
        assert [(e.field, e.code) for e in result.errors] == [("total_amount", "business.amount_exceeds_policy")]
        write_policy(path, 200000)
        accepted = ValidationResult.model_validate(client.post("/validate", json=RAW).json())
        assert accepted.valid is True
        assert accepted.normalized_values.model_dump() == EXPECTED
        path.write_text("{", encoding="utf-8")
        failure = client.post("/validate", json=RAW)
        assert failure.status_code == 503
        assert failure.json() == {"error": {"code": "invoice_policy_unavailable", "message": "Invoice policy is unavailable or invalid"}}
        assert "normalized_values" not in failure.json()
        assert str(path) not in failure.text


def test_tc10_concurrent_calls_and_order_have_no_shared_policy_state(tmp_path):
    low = write_policy(tmp_path / "low.json", 100000)
    high = write_policy(tmp_path / "high.json", 200000)
    paths = [low, high] * 50
    def outcome(path):
        result = validate(path)
        return result.valid, result.normalized_values.total_amount, tuple((e.field, e.code) for e in result.errors)
    expected = [(False, None, (("total_amount", "business.amount_exceeds_policy"),)), (True, 125000, ())] * 50
    with ThreadPoolExecutor(max_workers=20) as pool:
        assert list(pool.map(outcome, paths)) == expected
    assert [outcome(p) for p in reversed(paths)] == list(reversed(expected))


def test_tc11_no_clock_random_network_or_cwd_dependency(tmp_path, monkeypatch):
    import random
    import socket
    import time
    def forbidden(*args, **kwargs):
        raise AssertionError("Validation must not depend on clock/random/network")
    for obj, name in [(time, "time"), (time, "sleep"), (random, "random"), (socket, "create_connection")]:
        monkeypatch.setattr(obj, name, forbidden)
    monkeypatch.chdir(tmp_path)
    first = validation.validate_invoice(normalize_invoice(EXPECTED)).model_dump_json()
    assert validation.validate_invoice(normalize_invoice(EXPECTED)).model_dump_json() == first


def test_tc12_zero_ceiling_and_multiple_field_errors(tmp_path):
    path = write_policy(tmp_path / "policy.json", 0)
    assert validate(path, {**EXPECTED, "total_amount": 0}).valid is True
    result = validate(path, {**EXPECTED, "total_amount": 1, "currency": "USD"})
    assert result.valid is False
    assert {(e.field, e.code) for e in result.errors} == {("currency", "business.unsupported_currency"), ("total_amount", "business.amount_exceeds_policy")}


def test_tc13_existing_pipeline_consumer_honors_policy(tmp_path, monkeypatch):
    from app.providers.fake import FakeExtractionProvider
    from app.schemas.extraction import DocumentInput, PipelineSuccess
    from app.services.pipeline import run_pipeline
    path = write_policy(tmp_path / "policy.json", 100000)
    monkeypatch.setattr(validation, "DEFAULT_POLICY_PATH", path)
    result = run_pipeline(DocumentInput(document_id="vt045", media_type="image/png", content=b"synthetic-not-real-image"), FakeExtractionProvider())
    assert isinstance(result, PipelineSuccess)
    assert result.status == "succeeded"  # Extraction success is NOT business validity.
    assert result.validation.valid is False
    assert result.validation.normalized_values.total_amount is None
    assert [(e.field, e.code) for e in result.validation.errors] == [("total_amount", "business.amount_exceeds_policy")]
