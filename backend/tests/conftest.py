import os

# In-memory DB before any app imports bind the default engine.
os.environ["NEWSLETTER_DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.routers import issues
from app.routers.admin import router as admin_router


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
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
