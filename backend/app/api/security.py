from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import token_digest
from app.models import User, UserSession

settings = get_settings()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    session = db.get(UserSession, token_digest(raw)) if raw else None
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Vui lòng đăng nhập")
    expiry = session.expires_at
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Vui lòng đăng nhập")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập không hợp lệ")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if request.headers.get("X-CSRF-Token") != session.csrf_token:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF token không hợp lệ")
    return user
