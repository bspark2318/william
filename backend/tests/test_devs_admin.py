"""Tests for /api/admin/devs endpoints."""

from datetime import datetime, timezone
from unittest.mock import patch

from app.models import DevPost


@patch("app.routers.admin.collect_dev_candidates")
def test_trigger_devs_collect(mock_collect, client):
    mock_collect.return_value = {"hn": 5, "github": 3}
    r = client.post("/api/admin/devs/collect")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "stories_added": 8,
    }
    mock_collect.assert_called_once()


@patch("app.routers.admin.publish_dev_feed")
def test_trigger_devs_publish(mock_publish, client):
    mock_publish.return_value = {
        "hn_published": 3,
        "github_published": 2,
    }
    r = client.post("/api/admin/devs/publish")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "published"
    assert body["feed_size"] == 5
    mock_publish.assert_called_once()


@patch("app.routers.admin.publish_dev_feed")
def test_trigger_devs_publish_skipped_when_empty(mock_publish, client):
    mock_publish.return_value = {
        "hn_published": 0,
        "github_published": 0,
    }
    r = client.post("/api/admin/devs/publish")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "skipped"
    assert body["feed_size"] == 0


def test_devs_candidates_empty(client):
    r = client.get("/api/admin/devs/candidates")
    assert r.status_code == 200
    assert r.json() == []


def test_devs_candidates_populated(client, db_session):
    dev_hn = DevPost(
        source="hn",
        url="https://news.ycombinator.com/item?id=42",
        published_at=datetime.now(timezone.utc),
        collected_at=datetime.now(timezone.utc),
        title="A coding agent appears",
        is_active=False,
        display_order=None,
        rank_features={"heuristic": 0.7, "llm": 0.9},
        points=100,
        comments=10,
    )
    dev_gh = DevPost(
        source="github",
        url="https://github.com/foo/bar/releases/tag/v1",
        published_at=datetime.now(timezone.utc),
        collected_at=datetime.now(timezone.utc),
        title="foo/bar v1",
        is_active=True,
        display_order=1,
        repo="foo/bar",
        version="v1",
        stars=500,
    )
    db_session.add_all([dev_hn, dev_gh])
    db_session.commit()

    r = client.get("/api/admin/devs/candidates")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) == 2

    by_source = {row["source"]: row for row in rows}
    assert set(by_source) == {"hn", "github"}

    hn_row = by_source["hn"]
    assert hn_row["title"] == "A coding agent appears"
    assert hn_row["rank_features"] == {"heuristic": 0.7, "llm": 0.9}
    assert hn_row["is_active"] is False

    gh_row = by_source["github"]
    assert gh_row["title"] == "foo/bar v1"
    assert gh_row["is_active"] is True
    assert gh_row["display_order"] == 1
