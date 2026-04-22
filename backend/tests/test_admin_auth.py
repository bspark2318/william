"""Auth gate on /api/admin/* (GitHub #11).

The router-level `require_admin_token` dependency protects every admin route.
These tests cover the three failure modes + one happy-path smoke check.
"""

from unittest.mock import patch

import pytest

from app.routers import admin as admin_mod
from tests.conftest import TEST_ADMIN_TOKEN


# Every route under /api/admin/* is covered by the same dependency, so hitting
# one representative per group is sufficient. We pick a GET (read-only, safe)
# plus one POST per group to exercise both verbs.
_REPRESENTATIVE_ROUTES = [
    ("GET", "/api/admin/candidates"),
    ("GET", "/api/admin/devs/candidates"),
    ("GET", "/api/admin/devs/handle-stats"),
    ("GET", "/api/admin/devs/discovered-handles"),
    ("GET", "/api/admin/devs/budget"),
    ("POST", "/api/admin/collect"),
    ("POST", "/api/admin/publish"),
    ("POST", "/api/admin/devs/collect"),
    ("POST", "/api/admin/devs/publish"),
    ("POST", "/api/admin/devs/discovered-handles/ghost/add"),
    ("POST", "/api/admin/devs/discovered-handles/ghost/ignore"),
]


@pytest.mark.parametrize("method,url", _REPRESENTATIVE_ROUTES)
def test_missing_bearer_returns_401(unauth_client, method, url):
    r = unauth_client.request(method, url)
    assert r.status_code == 401
    assert r.headers.get("www-authenticate", "").lower().startswith("bearer")


@pytest.mark.parametrize("method,url", _REPRESENTATIVE_ROUTES)
def test_wrong_token_returns_401(unauth_client, method, url):
    r = unauth_client.request(
        method, url, headers={"Authorization": "Bearer not-the-real-token"}
    )
    assert r.status_code == 401


@pytest.mark.parametrize("method,url", _REPRESENTATIVE_ROUTES)
def test_non_bearer_scheme_returns_401(unauth_client, method, url):
    r = unauth_client.request(
        method, url, headers={"Authorization": f"Basic {TEST_ADMIN_TOKEN}"}
    )
    assert r.status_code == 401


@pytest.mark.parametrize("method,url", _REPRESENTATIVE_ROUTES)
def test_unconfigured_token_returns_503(unauth_client, monkeypatch, method, url):
    monkeypatch.setattr(admin_mod, "ADMIN_TOKEN", "")
    r = unauth_client.request(
        method, url, headers={"Authorization": f"Bearer {TEST_ADMIN_TOKEN}"}
    )
    assert r.status_code == 503


@patch("app.routers.admin.collect_dev_candidates")
def test_valid_token_reaches_handler(mock_collect, client):
    """Smoke test: with the auto-injected header, the handler runs normally."""
    mock_collect.return_value = {"hn": 1, "github": 0, "x": 0}
    r = client.post("/api/admin/devs/collect")
    assert r.status_code == 200
    assert r.json()["stories_added"] == 1
    mock_collect.assert_called_once()
