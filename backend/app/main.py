import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, ensure_sqlite_columns
from .routers import issues
from .routers.admin import router as admin_router
from .scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_columns()
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
