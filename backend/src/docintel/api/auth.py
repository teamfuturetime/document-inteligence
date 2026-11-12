"""Same-origin session endpoints; no registration or administrator HTTP endpoints."""

from fastapi import APIRouter, Request, Response

from docintel.api.auth_body import BoundedAuthRoute
from docintel.api.identity import COOKIE_NAME, COOKIE_PATH, check_csrf, require_session
from docintel.api.models import ErrorEnvelope
from docintel.domain.auth import Credentials, SessionState
from docintel.services.documents import ProductError

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"], route_class=BoundedAuthRoute)


@router.get("/session", response_model=SessionState)
def session(request: Request, response: Response):
    mode = request.app.state.documents.settings.auth_mode
    principal = (
        request.app.state.auth.session(request.cookies.get(COOKIE_NAME))
        if mode == "session"
        else None
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionState(
        mode=mode,
        user=principal.user if principal else None,
        csrf_token=principal.csrf_token if principal else None,
    )


@router.post(
    "/login",
    response_model=SessionState,
    responses={400: {"model": ErrorEnvelope}, 408: {"model": ErrorEnvelope}},
)
def login(request: Request, response: Response, body: Credentials):
    settings = request.app.state.documents.settings
    if settings.auth_mode != "session":
        raise ProductError(404, "AUTH_DISABLED", "Chế độ tài khoản chưa được bật.")
    if (
        request.headers.get("origin") not in settings.cors_origins
        or request.headers.get("x-requested-with") != "docintel"
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        raise ProductError(403, "LOGIN_ORIGIN_REJECTED", "Nguồn đăng nhập không hợp lệ.")
    raw, principal = request.app.state.auth.login(body, request.cookies.get(COOKIE_NAME))
    response.set_cookie(
        COOKIE_NAME,
        raw,
        max_age=settings.session_ttl_seconds,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionState(mode="session", user=principal.user, csrf_token=principal.csrf_token)


@router.post("/logout", status_code=204, response_class=Response)
def logout(request: Request, response: Response):
    settings = request.app.state.documents.settings
    if settings.auth_mode != "session":
        raise ProductError(404, "AUTH_DISABLED", "Chế độ tài khoản chưa được bật.")
    principal = require_session(request)
    check_csrf(request, principal)
    request.app.state.auth.logout(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
    response.status_code = 204
    response.headers["Cache-Control"] = "no-store"
    return response
