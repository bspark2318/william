import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")
_env_specific = os.getenv("DOTENV_FILE", ".env.dev")
load_dotenv(_BACKEND_ROOT / _env_specific, override=True)

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
        story_cols = conn.execute(text("PRAGMA table_info(stories)")).mappings().all()
        story_names = {r["name"] for r in story_cols}
        if "bullet_points" not in story_names:
            conn.execute(text("ALTER TABLE stories ADD COLUMN bullet_points TEXT"))

        video_cols = (
            conn.execute(text("PRAGMA table_info(candidate_videos)")).mappings().all()
        )
        video_names = {r["name"] for r in video_cols}
        _new_video_cols = {
            "view_count": "INTEGER",
            "duration_seconds": "INTEGER",
            "like_count": "INTEGER",
            "comment_count": "INTEGER",
            "engagement_rate": "REAL",
            "view_velocity": "REAL",
            "transcript_excerpt": "TEXT",
            "content_type": "TEXT",
        }
        if video_cols:
            for col, typ in _new_video_cols.items():
                if col not in video_names:
                    conn.execute(
                        text(f"ALTER TABLE candidate_videos ADD COLUMN {col} {typ}")
                    )

        for orphan in ("candidate_x_tweets", "x_topic_digests", "discovered_handles"):
            conn.execute(text(f"DROP TABLE IF EXISTS {orphan}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
