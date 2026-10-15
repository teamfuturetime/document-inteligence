import secrets

from fastapi import Header, HTTPException

from app.core.config import get_settings


def require_api_key(x_api_key: str | None = Header(None)) -> None:
    """Require a shared key when configured; local development remains simple."""
    expected = get_settings().api_key
    if expected and (not x_api_key or not secrets.compare_digest(x_api_key, expected)):
        raise HTTPException(status_code=401, detail="Không có quyền truy cập")
