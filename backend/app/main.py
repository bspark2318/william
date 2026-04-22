import logging
import os
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, ensure_sqlite_columns
from .models import DevPost, Issue, XTopicDigestRow
from .routers import devs, issues
from .routers.admin import router as admin_router
from .scheduler import start_scheduler, stop_scheduler
from .services.devs_pipeline import collect_dev_candidates, publish_dev_feed
from .services.pipeline import collect_candidates, publish_issue

logger = logging.getLogger(__name__)


def _bootstrap_pipeline(
    label: str,
    empty_check: Callable[[Session], bool],
    collect_fn: Callable[[Session], None],
    publish_fn: Callable[[Session], None],
) -> None:
    db = SessionLocal()
    try:
        if empty_check(db):
            logger.info("No %s data found — running startup collect + publish", label)
            try:
                collect_fn(db)
            except Exception:
                logger.exception("Startup %s collect failed — attempting publish with any saved candidates", label)
            try:
                publish_fn(db)
            except Exception:
                logger.exception("Startup %s publish failed", label)
    except Exception:
        logger.exception("Startup %s bootstrap failed", label)
    finally:
        db.close()


def _bootstrap_all_if_empty() -> None:
    """Sequentially bootstrap news then devs on cold start. Set BOOTSTRAP_ON_EMPTY=false to skip."""
    if os.getenv("BOOTSTRAP_ON_EMPTY", "true").lower() == "false":
        return

    _bootstrap_pipeline(
        "news",
        lambda db: db.query(Issue).first() is None,
        collect_candidates,
        publish_issue,
    )
    _bootstrap_pipeline(
        "devs",
        lambda db: not (db.query(DevPost).first() or db.query(XTopicDigestRow).first()),
        collect_dev_candidates,
        publish_dev_feed,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_columns()
    threading.Thread(target=_bootstrap_all_if_empty, daemon=True).start()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="AI Newsletter API", lifespan=lifespan)

_cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(issues.router)
app.include_router(devs.router)
app.include_router(admin_router)
