import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

SQLALCHEMY_DATABASE_URL = os.getenv(
    "NEWSLETTER_DATABASE_URL", "sqlite:///./newsletter.db"
)

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    _engine_kwargs: dict = {"connect_args": {"check_same_thread": False}}
    if SQLALCHEMY_DATABASE_URL.endswith(":memory:"):
        _engine_kwargs["poolclass"] = StaticPool
    engine = create_engine(SQLALCHEMY_DATABASE_URL, **_engine_kwargs)
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_sqlite_columns() -> None:
    """Add columns missing from older DB files (create_all does not ALTER)."""
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        return
    from sqlalchemy import text

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(stories)")).mappings().all()
        names = {r["name"] for r in rows}
        if "bullet_points" not in names:
            conn.execute(text("ALTER TABLE stories ADD COLUMN bullet_points TEXT"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
