import os

# In-memory DB before any app imports bind the default engine.
os.environ["NEWSLETTER_DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.routers import admin as admin_mod
from app.routers import issues
from app.routers.admin import router as admin_router

TEST_ADMIN_TOKEN = "test-admin-token"
ADMIN_HEADERS = {"Authorization": f"Bearer {TEST_ADMIN_TOKEN}"}


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def _admin_token(monkeypatch):
    monkeypatch.setattr(admin_mod, "ADMIN_TOKEN", TEST_ADMIN_TOKEN)
    yield


class _AdminClient(TestClient):
    """TestClient that injects the admin Bearer header on /api/admin/* calls."""

    def request(self, method, url, **kwargs):
        path = url if isinstance(url, str) else str(url)
        if path.startswith("/api/admin"):
            headers = dict(kwargs.pop("headers", None) or {})
            headers.setdefault("Authorization", f"Bearer {TEST_ADMIN_TOKEN}")
            kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(issues.router)
    app.include_router(admin_router)

    with _AdminClient(app) as tc:
        yield tc


@pytest.fixture
def unauth_client():
    """TestClient without auto-injected admin headers — for 401/503 tests."""
    app = FastAPI()
    app.include_router(issues.router)
    app.include_router(admin_router)

    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def db_session():
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
