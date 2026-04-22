"""Tests for GET /api/devs/posts.

These tests exercise the serving layer (Slice 3). They depend on ORM classes
`DevPost` / `XTopicDigestRow` and the Pydantic schemas defined by Slice 1.
When those symbols aren't yet present in the current worktree we skip the
module rather than fail; the harmonizer re-runs the suite after merge.
"""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

@pytest.fixture
def devs_client():
    from app.routers import devs

    app = FastAPI()
    app.include_router(devs.router)
    with TestClient(app) as tc:
        yield tc


def test_list_dev_posts_empty(devs_client):
    r = devs_client.get("/api/devs/posts")
    assert r.status_code == 200
    assert r.json() == []


def test_list_dev_posts_returns_union_and_is_ordered(devs_client, db_session):
    """Seed HN + GitHub DevPost rows + an XTopicDigestRow; expect union-shaped
    JSON ordered by display_order ascending, each item carrying the `source`
    discriminator."""
    from app.models import DevPost, XTopicDigestRow

    hn = DevPost(
        source="hn",
        url="https://news.ycombinator.com/item?id=1",
        published_at=datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 4, 18, 13, 0, tzinfo=timezone.utc),
        title="Show HN: A new coding agent",
        importance_score=8.0,
        rank_score=9.0,
        topics=["coding agent"],
        is_active=True,
        display_order=1,
        hn_url="https://news.ycombinator.com/item?id=1",
        points=420,
        comments=88,
        bullets=["great tool", "reviewers skeptical"],
        top_comment_excerpt="This is a top comment.",
    )
    gh = DevPost(
        source="github",
        url="https://github.com/anthropics/claude-code/releases/tag/v1.0.0",
        published_at=datetime(2026, 4, 17, 20, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 4, 17, 20, 30, tzinfo=timezone.utc),
        title="claude-code v1.0.0",
        importance_score=9.0,
        rank_score=9.5,
        topics=["coding agent"],
        is_active=True,
        display_order=4,
        repo="anthropics/claude-code",
        version="v1.0.0",
        release_bullets=["new sub-agents", "tool use improvements"],
        release_notes_excerpt="…",
        why_it_matters="Spec-driven agents get easier.",
        has_breaking_changes=False,
        stars=5000,
        stars_velocity_7d=120,
    )
    inactive = DevPost(
        source="hn",
        url="https://news.ycombinator.com/item?id=999",
        published_at=datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 4, 10, 13, 0, tzinfo=timezone.utc),
        title="Old HN story",
        is_active=False,
        display_order=99,
        hn_url="https://news.ycombinator.com/item?id=999",
        points=10,
        comments=1,
    )
    x_digest = XTopicDigestRow(
        topic="MCP patterns",
        bullets=[
            {
                "text": "Servers are converging on a standard transport.",
                "sources": [
                    {
                        "url": "https://x.com/user/status/1",
                        "author_handle": "karpathy",
                        "author_name": "Andrej",
                    }
                ],
            }
        ],
        rank_score=8.0,
        is_active=True,
        display_order=6,
        created_at=datetime(2026, 4, 18, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([hn, gh, inactive, x_digest])
    db_session.commit()

    r = devs_client.get("/api/devs/posts")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 3  # inactive row excluded

    # Ordered by display_order ascending across all three sources.
    orders = [item["display_order"] for item in body]
    assert orders == sorted(orders)
    assert orders == [1, 4, 6]

    # Every item carries a `source` discriminator.
    sources = [item["source"] for item in body]
    assert sources == ["hn", "github", "x"]

    hn_item = body[0]
    assert hn_item["title"] == "Show HN: A new coding agent"
    assert hn_item["points"] == 420
    assert hn_item["bullets"] == ["great tool", "reviewers skeptical"]

    gh_item = body[1]
    assert gh_item["repo"] == "anthropics/claude-code"
    assert gh_item["has_breaking_changes"] is False
    assert gh_item["release_bullets"] == ["new sub-agents", "tool use improvements"]

    x_item = body[2]
    assert x_item["topic"] == "MCP patterns"
    assert x_item["bullets"][0]["sources"][0]["author_handle"] == "karpathy"
    # X digests have no url / published_at per frontend contract.
    assert "url" not in x_item or x_item.get("url") is None


def test_publish_dev_feed_then_list_returns_published_rows(
    devs_client, db_session, monkeypatch
):
    """Boundary test: Slice 2 publisher writes rows that Slice 3 router serves.

    Seed pre-scored, inactive HN + GitHub candidates. Invoke the real
    publish_dev_feed (with external HN comment fetch + LLM insight calls
    stubbed). Expect /api/devs/posts to return the flipped-active rows
    with display_order assigned by the publisher.
    """
    from app.models import DevPost
    from app.services import devs_pipeline, devs_ranker

    # Stub external HN comment fetch so publish_hn runs offline.
    monkeypatch.setattr(devs_pipeline, "fetch_hn_comments", lambda _id: [])
    # Stub the GitHub LLM insight extraction to a deterministic payload.
    monkeypatch.setattr(
        devs_ranker,
        "extract_github_insights",
        lambda repo, notes: {
            "release_bullets": ["boundary bullet"],
            "why_it_matters": "integration matters",
            "has_breaking_changes": False,
        },
    )

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            DevPost(
                source="hn",
                url="https://news.ycombinator.com/item?id=10",
                published_at=now,
                collected_at=now,
                title="HN boundary candidate",
                importance_score=5.0,
                is_active=False,
                hn_url="https://news.ycombinator.com/item?id=10",
                points=150,
                comments=25,
            ),
            DevPost(
                source="github",
                url="https://github.com/foo/bar/releases/tag/v2.0.0",
                published_at=now,
                collected_at=now,
                title="foo/bar v2.0.0",
                importance_score=7.0,
                is_active=False,
                repo="foo/bar",
                version="v2.0.0",
                release_notes_excerpt="notes",
            ),
        ]
    )
    db_session.commit()

    result = devs_pipeline.publish_dev_feed(db_session)
    assert result is not None
    assert result["hn_published"] >= 1
    assert result["github_published"] >= 1

    r = devs_client.get("/api/devs/posts")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2

    # HN gets slot 1, GitHub gets slot 4 per publish_dev_feed's slot math.
    orders = [item["display_order"] for item in body]
    assert orders == sorted(orders)
    assert 1 in orders and 4 in orders

    sources = {item["source"] for item in body}
    assert sources == {"hn", "github"}

    gh_item = next(i for i in body if i["source"] == "github")
    assert gh_item["release_bullets"] == ["boundary bullet"]
    assert gh_item["why_it_matters"] == "integration matters"


def test_admin_collect_trigger_invokes_pipeline_orchestrator(db_session, monkeypatch):
    """Boundary test: POST /api/admin/devs/collect actually calls collect_dev_candidates.

    Verifies Slice 3 admin wiring and Slice 2 pipeline entrypoint agree on name
    and signature (no ImportError, callable receives a Session, result shape
    surfaces through the HTTP layer).
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.routers.admin import router as admin_router
    from app.services import devs_pipeline

    called_with = {}

    def fake_collect(db):
        called_with["db_type"] = type(db).__name__
        return {"hn": 1, "github": 2, "x": 3}

    monkeypatch.setattr(devs_pipeline, "collect_dev_candidates", fake_collect)
    # The admin router imports the symbol at module load — patch the reference too.
    import app.routers.admin as admin_mod

    monkeypatch.setattr(admin_mod, "collect_dev_candidates", fake_collect)

    app = FastAPI()
    app.include_router(admin_router)

    from tests.conftest import ADMIN_HEADERS

    with TestClient(app) as tc:
        r = tc.post("/api/admin/devs/collect", headers=ADMIN_HEADERS)

    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "stories_added": 3,
        "videos_added": 0,
        "tweets_added": 3,
    }
    assert called_with["db_type"] == "Session"
