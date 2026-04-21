"""Tests for /api/admin/devs endpoints (Slice 3).

These cover the admin surface: trigger collect/publish, candidates listing,
handle stats, discovered-handles list/add/ignore (incl. cap enforcement),
and the budget endpoint.

Requires Slice 1 ORM models (DevPost, CandidateXTweet, XTopicDigestRow,
DiscoveredHandle) and Slice 2 pipeline entrypoints (collect_dev_candidates,
publish_dev_feed). When missing we skip the module — the harmonizer re-runs
the suite after merge.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.models import (
    CandidateXTweet,
    DevPost,
    DiscoveredHandle,
)


@pytest.fixture
def devs_yaml_tmp(tmp_path, monkeypatch):
    """Point the admin router at a temp devs_config.yaml for add/ignore tests."""
    import app.routers.admin as admin_mod

    cfg_path = tmp_path / "devs_config.yaml"
    monkeypatch.setattr(admin_mod, "_DEVS_CONFIG_PATH", cfg_path)
    return cfg_path


@patch("app.routers.admin.collect_dev_candidates")
def test_trigger_devs_collect(mock_collect, client):
    mock_collect.return_value = {"hn": 5, "github": 3, "x": 20}
    r = client.post("/api/admin/devs/collect")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "stories_added": 8,
        "videos_added": 0,
        "tweets_added": 20,
    }
    mock_collect.assert_called_once()


@patch("app.routers.admin.publish_dev_feed")
def test_trigger_devs_publish(mock_publish, client):
    mock_publish.return_value = {
        "hn_published": 3,
        "github_published": 2,
        "x_published": 3,
    }
    r = client.post("/api/admin/devs/publish")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "published"
    assert body["feed_size"] == 8
    assert body["digest_title"]
    mock_publish.assert_called_once()


@patch("app.routers.admin.publish_dev_feed")
def test_trigger_devs_publish_skipped_when_empty(mock_publish, client):
    mock_publish.return_value = {
        "hn_published": 0,
        "github_published": 0,
        "x_published": 0,
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
    dev = DevPost(
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
    tweet = CandidateXTweet(
        url="https://x.com/foo/status/1",
        author_handle="foo",
        author_name="Foo",
        text="MCP is cool",
        likes=50,
        reposts=5,
        replies=2,
        published_at=datetime.now(timezone.utc),
        collected_at=datetime.now(timezone.utc),
        quality_score=7.5,
        topic_cluster=None,
        used_in_digest_id=None,
    )
    db_session.add_all([dev, tweet])
    db_session.commit()

    r = client.get("/api/admin/devs/candidates")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) == 2

    by_source = {row["source"]: row for row in rows}
    assert set(by_source) == {"hn", "x"}

    hn_row = by_source["hn"]
    assert hn_row["title"] == "A coding agent appears"
    assert hn_row["text"] is None
    assert hn_row["rank_features"] == {"heuristic": 0.7, "llm": 0.9}
    assert hn_row["is_active"] is False

    x_row = by_source["x"]
    assert x_row["title"] is None
    assert x_row["text"] == "MCP is cool"
    assert x_row["rank_score"] == 7.5
    assert x_row["is_active"] is False  # used_in_digest_id is None


def test_devs_handle_stats(client, db_session):
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            CandidateXTweet(
                url="https://x.com/a/status/1",
                author_handle="alpha",
                text="t1",
                published_at=now,
                collected_at=now,
                quality_score=7.0,
                used_in_digest_id=1,
            ),
            CandidateXTweet(
                url="https://x.com/a/status/2",
                author_handle="alpha",
                text="t2",
                published_at=now,
                collected_at=now,
                quality_score=4.0,
                used_in_digest_id=None,
            ),
            CandidateXTweet(
                url="https://x.com/b/status/1",
                author_handle="beta",
                text="t3",
                published_at=now,
                collected_at=now,
                quality_score=8.0,
                used_in_digest_id=None,
            ),
        ]
    )
    db_session.commit()

    r = client.get("/api/admin/devs/handle-stats")
    assert r.status_code == 200
    handles = r.json()
    assert isinstance(handles, list)
    by_handle = {h["handle"]: h for h in handles}

    assert by_handle["alpha"]["tweets_collected_30d"] == 2
    assert by_handle["alpha"]["tweets_scored_above_6_30d"] == 1
    assert by_handle["alpha"]["tweets_published_30d"] == 1
    assert by_handle["beta"]["tweets_collected_30d"] == 1
    assert by_handle["beta"]["tweets_scored_above_6_30d"] == 1
    assert by_handle["beta"]["tweets_published_30d"] == 0

    # Sorted ascending by tweets_published_30d (beta=0 before alpha=1).
    assert handles[0]["handle"] == "beta"


def test_devs_discovered_handles_list_pending(client, db_session):
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            DiscoveredHandle(
                handle="new_a",
                first_seen_at=now,
                last_seen_at=now,
                seed_engagement_count=12,
                seed_handles=["karpathy"],
                status="pending",
            ),
            DiscoveredHandle(
                handle="old_b",
                first_seen_at=now,
                last_seen_at=now,
                seed_engagement_count=3,
                seed_handles=["simonw"],
                status="ignored",
            ),
        ]
    )
    db_session.commit()

    r = client.get("/api/admin/devs/discovered-handles?status=pending")
    assert r.status_code == 200
    handles = r.json()
    assert isinstance(handles, list)
    assert len(handles) == 1
    assert handles[0]["handle"] == "new_a"


def test_discovered_handle_add_writes_yaml_and_flips_status(
    client, db_session, devs_yaml_tmp
):
    import yaml

    db_session.add(
        DiscoveredHandle(
            handle="fresh_handle",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            seed_engagement_count=10,
            seed_handles=["karpathy"],
            status="pending",
        )
    )
    db_session.commit()

    # Seed yaml with a few existing handles.
    devs_yaml_tmp.write_text(
        yaml.safe_dump(
            {"x_handles": {"tier_a": ["karpathy", "simonw"], "tier_b": ["rasbt"]}}
        )
    )

    r = client.post("/api/admin/devs/discovered-handles/fresh_handle/add")
    assert r.status_code == 200
    body = r.json()
    assert body["handle"] == "fresh_handle"
    assert body["status"] == "added"
    assert body["total_handles"] == 4

    cfg = yaml.safe_load(devs_yaml_tmp.read_text())
    assert "fresh_handle" in cfg["x_handles"]["tier_b"]

    # DB row status updated.
    row = (
        db_session.query(DiscoveredHandle)
        .filter(DiscoveredHandle.handle == "fresh_handle")
        .first()
    )
    db_session.refresh(row)
    assert row.status == "added"


def test_discovered_handle_add_enforces_cap(
    client, db_session, devs_yaml_tmp, monkeypatch
):
    import yaml

    import app.routers.admin as admin_mod

    # Shrink the cap for the test.
    monkeypatch.setattr(admin_mod, "MAX_X_HANDLES", 2)

    db_session.add(
        DiscoveredHandle(
            handle="one_too_many",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            seed_engagement_count=7,
            seed_handles=["karpathy"],
            status="pending",
        )
    )
    db_session.commit()

    devs_yaml_tmp.write_text(
        yaml.safe_dump({"x_handles": {"tier_a": ["alice", "bob"]}})
    )

    r = client.post("/api/admin/devs/discovered-handles/one_too_many/add")
    assert r.status_code == 400
    assert "MAX_X_HANDLES" in r.json()["detail"]

    # YAML untouched.
    cfg = yaml.safe_load(devs_yaml_tmp.read_text())
    assert "one_too_many" not in cfg["x_handles"].get("tier_a", [])
    assert "one_too_many" not in cfg["x_handles"].get("tier_b", [])


def test_discovered_handle_add_404_when_missing(client, devs_yaml_tmp):
    import yaml

    devs_yaml_tmp.write_text(yaml.safe_dump({"x_handles": {"tier_a": []}}))
    r = client.post("/api/admin/devs/discovered-handles/ghost/add")
    assert r.status_code == 404


def test_discovered_handle_ignore(client, db_session):
    db_session.add(
        DiscoveredHandle(
            handle="spam_acct",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            seed_engagement_count=5,
            seed_handles=["karpathy"],
            status="pending",
        )
    )
    db_session.commit()

    r = client.post("/api/admin/devs/discovered-handles/spam_acct/ignore")
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"

    row = (
        db_session.query(DiscoveredHandle)
        .filter(DiscoveredHandle.handle == "spam_acct")
        .first()
    )
    db_session.refresh(row)
    assert row.status == "ignored"


def test_devs_budget_empty(client):
    r = client.get("/api/admin/devs/budget")
    assert r.status_code == 200
    body = r.json()
    assert body["tweets_used_30d"] == 0
    assert body["tweets_cap"] >= 1
    assert body["remaining"] == body["tweets_cap"]
    assert body["pct_used"] == 0.0
    assert body["will_pause_at"] is None


def test_devs_budget_counts_last_30_days(client, db_session, monkeypatch):
    import app.routers.admin as admin_mod

    monkeypatch.setattr(admin_mod, "APIFY_MONTHLY_TWEET_CAP", 3)

    now = datetime.now(timezone.utc)
    long_ago = now - timedelta(days=60)
    db_session.add_all(
        [
            CandidateXTweet(
                url=f"https://x.com/x/status/{i}",
                author_handle="x",
                text="t",
                published_at=now,
                collected_at=now,
            )
            for i in range(3)
        ]
        + [
            CandidateXTweet(
                url="https://x.com/x/status/old",
                author_handle="x",
                text="old",
                published_at=long_ago,
                collected_at=long_ago,
            )
        ]
    )
    db_session.commit()

    r = client.get("/api/admin/devs/budget")
    assert r.status_code == 200
    body = r.json()
    assert body["tweets_used_30d"] == 3
    assert body["tweets_cap"] == 3
    assert body["remaining"] == 0
    assert body["pct_used"] == 100.0
    assert body["will_pause_at"] is not None
