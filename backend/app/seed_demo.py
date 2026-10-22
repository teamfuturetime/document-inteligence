"""Create a development-only demo user from explicit environment variables."""
import os
from sqlalchemy import or_, select
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User

def main() -> None:
    settings = get_settings()
    if settings.APP_ENV.lower() == "production":
        raise SystemExit("Không được seed tài khoản demo trong production")
    email = os.environ.get("DEMO_USER_EMAIL")
    username = os.environ.get("DEMO_USER_NAME", "demo")
    password = os.environ.get("DEMO_USER_PASSWORD")
    if not email or not password or len(password) < 10:
        raise SystemExit("Cần DEMO_USER_EMAIL và DEMO_USER_PASSWORD (ít nhất 10 ký tự)")
    with SessionLocal() as db:
        existing = db.execute(select(User).where(or_(User.email == email.lower(), User.username == username))).scalar_one_or_none()
        if existing:
            print("Tài khoản demo đã tồn tại")
            return
        db.add(User(email=email.lower(), username=username, password_hash=hash_password(password)))
        db.commit()
        print(f"Đã tạo tài khoản demo: {username}")

if __name__ == "__main__":
    main()
