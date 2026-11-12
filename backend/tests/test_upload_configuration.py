import pytest
from pydantic import ValidationError

from docintel.config import Settings


@pytest.mark.parametrize("value", [0, -1, 121, float("inf")])
def test_invalid_receive_budget_is_rejected(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, upload_receive_timeout_seconds=value)


@pytest.mark.parametrize("value", [0, -1, 9])
def test_invalid_admission_budget_is_rejected(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_concurrent_uploads=value)
