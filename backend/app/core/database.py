"""Database engine, session factory và Base declarative."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Pool phù hợp với ràng buộc 421 người dùng đồng thời (chỉ cho PostgreSQL)
_engine_kwargs: dict = {"pool_pre_ping": True}
if settings.DATABASE_URL.startswith("postgresql"):
    _engine_kwargs.update({"pool_size": 10, "max_overflow": 20, "pool_recycle": 1800})

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class cho tất cả SQLAlchemy models."""


def get_db():
    """Dependency FastAPI: yield một database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

