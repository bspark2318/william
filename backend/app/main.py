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

from .models import DevPost, XTopicDigestRow
from .services.devs_pipeline import collect_dev_candidates, publish_dev_feed

logger = logging.getLogger(__name__)


def _bootstrap_all_if_empty() -> None:
    """Sequentially bootstrap news then devs on cold start. Set BOOTSTRAP_ON_EMPTY=false to skip."""
    if os.getenv("BOOTSTRAP_ON_EMPTY", "true").lower() == "false":
        return

    db = SessionLocal()
    try:
        if db.query(Issue).first() is None:
            logger.info("No issues found — running startup collect + publish")
            try:
                collect_candidates(db)
            except Exception:
                logger.exception("Startup collect failed — attempting publish with any saved candidates")
            publish_issue(db)

        has_dev_posts = db.query(DevPost).first() is not None
        has_x_digests = db.query(XTopicDigestRow).first() is not None
        if not has_dev_posts and not has_x_digests:
            logger.info("No devs posts found — running startup devs collect + publish")
            try:
                collect_dev_candidates(db)
            except Exception:
                logger.exception(
                    "Startup devs collect failed — attempting publish with any saved candidates"
                )
            publish_dev_feed(db)
    except Exception:
        logger.exception("Startup bootstrap failed")
    finally:
        db.close()


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
