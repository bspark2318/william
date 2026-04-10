import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, SessionLocal, engine, ensure_sqlite_columns
from .models import Issue
from .routers import issues
from .routers.admin import router as admin_router
from .scheduler import start_scheduler, stop_scheduler
from .services.pipeline import collect_candidates, publish_issue

logger = logging.getLogger(__name__)


def _bootstrap_if_empty() -> None:
    """Run collect + publish on first start when the DB has no issues."""
    db = SessionLocal()
    try:
        if db.query(Issue).first() is not None:
            return
        logger.info("No issues found — running startup collect + publish")
        collect_candidates(db)
        publish_issue(db)
    except Exception:
        logger.exception("Startup bootstrap failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_columns()
    _bootstrap_if_empty()
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
app.include_router(admin_router)
