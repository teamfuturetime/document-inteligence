from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.security import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password, new_token, token_digest, verify_password
from app.models import User, UserSession
from app.schemas.auth import AuthOut, Credentials, RegisterRequest, UserOut

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(settings.SESSION_COOKIE_NAME, token, httponly=True, secure=settings.SESSION_COOKIE_SECURE, samesite="lax", max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/")


def _create_session(db: Session, user: User) -> tuple[str, str]:
    raw_token, csrf = new_token(), new_token()
    db.add(UserSession(id=token_digest(raw_token), user_id=user.id, csrf_token=csrf, expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)))
    db.commit()
    return raw_token, csrf


@router.post("/register", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    user = User(email=payload.email.lower(), username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
        token, csrf = _create_session(db, user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Email hoặc tên đăng nhập đã tồn tại") from exc
    _set_cookie(response, token)
    return AuthOut(user=user, csrf_token=csrf)


@router.post("/login", response_model=AuthOut)
def login(payload: Credentials, response: Response, db: Session = Depends(get_db)):
    value = payload.login.strip()
    user = db.execute(select(User).where(or_(User.email == value.lower(), User.username == value))).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Thông tin đăng nhập không chính xác")
    token, csrf = _create_session(db, user)
    _set_cookie(response, token)
    return AuthOut(user=user, csrf_token=csrf)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if raw:
        session = db.get(UserSession, token_digest(raw))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")


@router.get("/me", response_model=AuthOut)
def me(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    session = db.get(UserSession, token_digest(raw))
    return AuthOut(user=user, csrf_token=session.csrf_token)
