import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, SessionLocal, engine, ensure_sqlite_columns
from .models import Issue
from .routers import devs, issues
from .routers.admin import router as admin_router
from .scheduler import start_scheduler, stop_scheduler
from .services.pipeline import collect_candidates, publish_issue

# Slice 1/2 symbols — defensively imported so this module still loads when
# those slices haven't landed yet.
try:
    from .models import DevPost, XTopicDigestRow  # type: ignore
    from .services.devs_pipeline import (  # type: ignore
        collect_dev_candidates,
        publish_dev_feed,
    )

    _DEVS_READY = True
except ImportError:  # pragma: no cover - resolved at merge time
    DevPost = None  # type: ignore
    XTopicDigestRow = None  # type: ignore
    collect_dev_candidates = None  # type: ignore
    publish_dev_feed = None  # type: ignore
    _DEVS_READY = False

logger = logging.getLogger(__name__)


def _bootstrap_if_empty() -> None:
    """Run collect + publish on first start when the DB has no issues."""
    db = SessionLocal()
    try:
        if db.query(Issue).first() is not None:
            return
        logger.info("No issues found — running startup collect + publish")
        try:
            collect_candidates(db)
        except Exception:
            logger.exception("Startup collect failed — attempting publish with any saved candidates")
        publish_issue(db)
    except Exception:
        logger.exception("Startup bootstrap failed")
    finally:
        db.close()


def _bootstrap_devs_if_empty() -> None:
    """Run devs collect + publish on first start when both devs tables are empty."""
    if not _DEVS_READY:
        return
    db = SessionLocal()
    try:
        has_dev_posts = db.query(DevPost).first() is not None
        has_x_digests = db.query(XTopicDigestRow).first() is not None
        if has_dev_posts or has_x_digests:
            return
        logger.info("No devs posts found — running startup devs collect + publish")
        try:
            collect_dev_candidates(db)
        except Exception:
            logger.exception(
                "Startup devs collect failed — attempting publish with any saved candidates"
            )
        publish_dev_feed(db)
    except Exception:
        logger.exception("Startup devs bootstrap failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_columns()
    threading.Thread(target=_bootstrap_if_empty, daemon=True).start()
    threading.Thread(target=_bootstrap_devs_if_empty, daemon=True).start()
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
