"""Request identity/CSRF gates; never mutate the shared application service principal."""

import re
import secrets

from fastapi import Request

from docintel.services.auth import Principal
from docintel.services.documents import ProductError

COOKIE_NAME = "docintel_session"
COOKIE_PATH = "/api/v1"


def require_session(request: Request) -> Principal:
    principal = request.app.state.auth.session(request.cookies.get(COOKIE_NAME))
    if principal is None:
        raise ProductError(401, "AUTH_REQUIRED", "Vui lòng đăng nhập.")
    return principal


def check_csrf(request: Request, principal: Principal):
    settings = request.app.state.documents.settings
    origin = request.headers.get("origin")
    supplied = request.headers.get("x-csrf-token", "")
    if (
        request.headers.get("sec-fetch-site") == "cross-site"
        or (origin is not None and origin not in settings.cors_origins)
        or not re.fullmatch(r"[A-Za-z0-9_-]{43}", supplied)
        or not secrets.compare_digest(supplied, principal.csrf_token)
    ):
        raise ProductError(403, "CSRF_REJECTED", "Yêu cầu xác thực không hợp lệ.")


def require_identity(request: Request) -> str:
    settings = request.app.state.documents.settings
    if settings.auth_mode == "local":
        owner = "local"
    else:
        principal = require_session(request)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            check_csrf(request, principal)
        owner = principal.user.id
    request.state.owner_id = owner
    return owner
